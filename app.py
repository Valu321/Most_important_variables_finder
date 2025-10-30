import streamlit as st
import pandas as pd
import numpy as np
from pycaret.classification import *
from pycaret.regression import *
import plotly.express as px
import plotly.graph_objects as go
from sklearn.model_selection import train_test_split
import openai
import os
from dotenv import load_dotenv
from langfuse.decorators import langfuse_context, observe
from langfuse.openai import openai as langfuse_openai
import warnings
warnings.filterwarnings('ignore')

# Załaduj zmienne środowiskowe
load_dotenv()

# Konfiguracja Langfuse
try:
    LANGFUSE_PUBLIC_KEY = os.getenv('LANGFUSE_PUBLIC_KEY')
    LANGFUSE_SECRET_KEY = os.getenv('LANGFUSE_SECRET_KEY')
    LANGFUSE_HOST = os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')
    
    if LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY:
        langfuse_openai.api_key = os.getenv('OPENAI_API_KEY')
        langfuse_openai.langfuse.public_key = LANGFUSE_PUBLIC_KEY
        langfuse_openai.langfuse.secret_key = LANGFUSE_SECRET_KEY
        langfuse_openai.langfuse.host = LANGFUSE_HOST
        LANGFUSE_ENABLED = True
    else:
        LANGFUSE_ENABLED = False
except:
    LANGFUSE_ENABLED = False

# Konfiguracja strony
st.set_page_config(
    page_title="Analiza Najważniejszych Cech",
    page_icon="📊",
    layout="wide"
)

# Tytuł aplikacji
st.title("📊 Aplikacja do znajdowania najważniejszych cech w zbiorze danych")
st.markdown("---")

# Funkcja do określenia typu problemu
def determine_problem_type(data, target_column):
    """Określa czy problem to klasyfikacja czy regresja."""
    target_data = data[target_column]

    # Jeśli ma mało unikalnych wartości względem rozmiaru zbioru → klasyfikacja
    unique_values = target_data.nunique(dropna=True)
    total_values = len(target_data)
    if total_values > 0 and unique_values / total_values < 0.2:
        return "klasyfikacja"

    # Jeżeli większość wartości daje się bezpiecznie zrzutować na liczby → regresja
    numeric_data = pd.to_numeric(target_data, errors='coerce')
    non_numeric_ratio = numeric_data.isna().mean()
    if non_numeric_ratio < 0.1:
        return "regresja"

    return "klasyfikacja"

# Funkcja do analizy ważności cech
def analyze_feature_importance(data, target_column, problem_type):
    """Analizuje ważność cech używając PyCaret"""
    
    # Przygotowanie danych
    
    # 1. Usuń kolumny z dużą liczbą wartości brakujących
    data_clean = data.dropna(thresh=len(data) * 0.7, axis=1)
    
    # 2. Usuń wiersze z wartościami brakującymi
    data_clean = data_clean.dropna()

    # 3. Sprawdź, czy kolumna docelowa przetrwała czyszczenie
    if target_column not in data_clean.columns:
        return None, f"Kolumna docelowa '{target_column}' została usunięta podczas czyszczenia (prawdopodobnie miała zbyt wiele brakujących wartości)."

    if len(data_clean) < 10:
        return None, "Za mało danych po czyszczeniu"
    
    # === POCZĄTEK POPRAWIONEGO BLOKU ===
    # Ten blok 'try...except' musi być WEWNĄTRZ funkcji
    try:
        if problem_type == "klasyfikacja":
            # Konfiguracja PyCaret dla klasyfikacji
            # Zmieniono nazwę zmiennej, aby uniknąć konfliktu z importem (clf)
            setup_env = setup(
                data_clean,
                target=target_column,
                session_id=123
            )
            
            # Porównanie modeli
            best_model = compare_models(include=['rf', 'xgboost', 'lightgbm'], verbose=False)
            
            # === POPRAWIONA LOGIKA ===
            # Pobierz nazwy cech BEZPOŚREDNIO z PyCaret (po transformacjach)
            feature_names = get_config('X_train_transformed').columns
            
            # Pobierz ważności z modelu
            importances = best_model.feature_importances_ if hasattr(best_model, 'feature_importances_') else [0] * len(feature_names)
            
            # Sprawdzenie (choć teraz powinno być zawsze równe)
            if len(feature_names) != len(importances):
                 return None, f"Błąd wewnętrzny: Niezgodność cech ({len(feature_names)}) i ważności ({len(importances)})."

            # Tworzenie DataFrame
            importance_df = pd.DataFrame({
                'Feature': feature_names,
                'Importance': importances
            })
            
        else:  # regresja
            # Konfiguracja PyCaret dla regresji
            # Zmieniono nazwę zmiennej
            setup_env = setup(
                data_clean,
                target=target_column,
                session_id=123
            )
            
            # Porównanie modeli
            best_model = compare_models(include=['rf', 'xgboost', 'lightgbm'], verbose=False)
            
            # === POPRAWIONA LOGIKA ===
            # Pobierz nazwy cech BEZPOŚREDNIO z PyCaret (po transformacjach)
            feature_names = get_config('X_train_transformed').columns
            
            # Pobierz ważności z modelu
            importances = best_model.feature_importances_ if hasattr(best_model, 'feature_importances_') else [0] * len(feature_names)

            # Sprawdzenie
            if len(feature_names) != len(importances):
                 return None, f"Błąd wewnętrzny: Niezgodność cech ({len(feature_names)}) i ważności ({len(importances)})."

            # Tworzenie DataFrame
            importance_df = pd.DataFrame({
                'Feature': feature_names,
                'Importance': importances
            })
        
        # Sortuj według ważności
        importance_df = importance_df.sort_values('Importance', ascending=False)
        
        return importance_df, best_model
        
    except Exception as e:
        return None, f"Błąd podczas analizy: {str(e)}"
    # === KONIEC POPRAWIONEGO BLOKU ===

# Funkcja do generowania opisu przez OpenAI
def generate_description_with_gpt(importance_df, problem_type, target_column, data_info, api_key=None):
    """Generuje opis słowny wyników używając OpenAI API"""
    
    if importance_df is None or len(importance_df) == 0:
        return "Nie udało się wygenerować opisu z powodu błędów w analizie."
    
    # Sprawdź czy klucz API jest dostępny (z parametru lub z pliku .env)
    if not api_key:
        api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        return """
## ⚠️ Brak klucza API

Aby wygenerować opis przez ChatGPT, wprowadź klucz OpenAI API w panelu po lewej stronie lub dodaj go do pliku `.env`.

**Tymczasowy opis:**
Najważniejsze cechy zostały zidentyfikowane w tabeli powyżej. 
Najwyższa ważność: **{0}** ({1:.1f}%).
        """.format(
            importance_df.iloc[0]['Feature'],
            (importance_df.iloc[0]['Importance'] / importance_df['Importance'].sum()) * 100
        )
    
    try:
        # Konfiguracja OpenAI - nowy interfejs z Langfuse
        from openai import OpenAI
        
        # Użyj Langfuse wrapper jeśli jest skonfigurowany
        if LANGFUSE_ENABLED:
            client = langfuse_openai
        else:
            client = OpenAI(api_key=api_key)
        
        # Przygotuj dane dla GPT
        top_features = importance_df.head(10)
        features_text = "\n".join([
            f"{i+1}. {row['Feature']}: {row['Importance']:.4f}" 
            for i, (_, row) in enumerate(top_features.iterrows())
        ])
        
        # Prompt dla GPT
        prompt = f"""
Jesteś ekspertem w analizie danych i machine learning. Przeanalizuj wyniki analizy ważności cech i wygeneruj profesjonalny opis.

DANE:
- Typ problemu: {problem_type}
- Kolumna docelowa: {target_column}
- Liczba cech: {len(importance_df)}
- Informacje o danych: {data_info}

NAJWAŻNIEJSZE CECHY:
{features_text}

Wygeneruj opis zawierający:
1. Podsumowanie analizy
2. Interpretację najważniejszych cech
3. Praktyczne wnioski biznesowe
4. Konkretne rekomendacje

Odpowiedz w języku polskim, w formacie Markdown, profesjonalnie ale przystępnie.
"""
        
        # Wywołanie API - z obsługą Langfuse
        if LANGFUSE_ENABLED:
            # Użyj wrappera Langfuse do automatycznego śledzenia
            langfuse_context.update_current_trace(
                name="generate_feature_analysis",
                user_id=st.session_state.get('user_id', 'anonymous'),
                metadata={
                    'problem_type': problem_type,
                    'target_column': target_column,
                    'num_features': len(importance_df)
                }
            )
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Jesteś ekspertem w analizie danych i machine learning. Odpowiadaj profesjonalnie w języku polskim."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        return f"## 🤖 Analiza wygenerowana przez ChatGPT\n\n{response.choices[0].message.content}"
        
    except Exception as e:
        return f"""
## ❌ Błąd podczas generowania opisu

Nie udało się wygenerować opisu przez ChatGPT: {str(e)}

**Podstawowe informacje:**
- Typ problemu: {problem_type}
- Kolumna docelowa: {target_column}
- Najważniejsza cecha: {importance_df.iloc[0]['Feature']}
- Liczba analizowanych cech: {len(importance_df)}
        """

# Główna aplikacja
def main():
    # Sidebar dla wczytywania pliku
    st.sidebar.header("📁 Wczytaj dane")
    
    uploaded_file = st.sidebar.file_uploader(
        "Wybierz plik CSV",
        type=['csv'],
        help="Wczytaj plik CSV z danymi do analizy"
    )
    
    # Pole do wprowadzenia klucza OpenAI API
    st.sidebar.header("🔑 Konfiguracja ChatGPT")
    openai_api_key = st.sidebar.text_input(
        "Klucz OpenAI API (opcjonalnie)",
        type="password",
        help="Wprowadź klucz API, aby korzystać z automatycznego generowania opisów przez ChatGPT"
    )
    
    if uploaded_file is not None:
        try:
            # Wczytanie danych
            data = pd.read_csv(uploaded_file, sep=None, engine='python')
            
            st.sidebar.success(f"✅ Wczytano {len(data)} wierszy i {len(data.columns)} kolumn")
            
            # Wyświetlenie podstawowych informacji o danych
            st.header("📊 Podgląd danych")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Pierwsze 5 wierszy")
                st.dataframe(data.head())
            
            with col2:
                st.subheader("Podstawowe statystyki")
                st.dataframe(data.describe())
            
            # Wybór kolumny docelowej
            st.header("🎯 Wybór kolumny docelowej")
            
            target_column = st.selectbox(
                "Wybierz kolumnę docelową:",
                options=data.columns,
                help="Wybierz kolumnę, dla której chcesz znaleźć najważniejsze cechy"
            )
            
            if st.button("🔍 Rozpocznij analizę", type="primary"):
                with st.spinner("Analizuję dane..."):
                    # Określenie typu problemu
                    problem_type = determine_problem_type(data, target_column)
                    
                    st.header(f"🤖 Typ problemu: {problem_type.title()}")
                    st.info(f"System automatycznie rozpoznał, że to problem **{problem_type}**")
                    
                    # Analiza ważności cech
                    importance_df, model = analyze_feature_importance(data, target_column, problem_type)
                    
                    if importance_df is not None:
                        st.header("📈 Najważniejsze cechy")
                        
                        # Wykres ważności cech
                        fig = px.bar(
                            importance_df.head(10),
                            x='Importance',
                            y='Feature',
                            orientation='h',
                            title="Top 10 najważniejszych cech",
                            color='Importance',
                            color_continuous_scale='viridis'
                        )
                        fig.update_layout(height=500)
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Tabela z wynikami
                        st.subheader("📋 Szczegółowe wyniki")
                        st.dataframe(importance_df, use_container_width=True)
                        
                        # Generowanie opisu przez ChatGPT
                        st.header("📝 Opis wyników")
                        
                        # Przygotuj informacje o danych
                        data_info = f"Zbiór zawiera {len(data)} wierszy i {len(data.columns)} kolumn. Typ problemu: {problem_type}."
                        
                        with st.spinner("🤖 Generuję opis przez ChatGPT..."):
                            description = generate_description_with_gpt(importance_df, problem_type, target_column, data_info, openai_api_key)
                            st.markdown(description)
                        
                    else:
                        st.error(f"❌ {model}")
                        
        except Exception as e:
            st.error(f"❌ Błąd podczas wczytywania pliku: {str(e)}")
    
    else:
        # Instrukcje dla użytkownika
        st.info("👆 Wczytaj plik CSV z danymi, aby rozpocząć analizę")
        
        st.markdown("""
        ## 🚀 Jak używać aplikacji:
        
        1. **Wczytaj dane** - użyj panelu po lewej stronie, aby wczytać plik CSV
        2. **Wybierz kolumnę docelową** - określ, którą kolumnę chcesz przewidywać
        3. **Rozpocznij analizę** - aplikacja automatycznie:
           - Określi typ problemu (klasyfikacja/regresja)
           - Zbuduje najlepszy model
           - Wyświetli najważniejsze cechy
           - Wygeneruje opis wyników przez ChatGPT 🤖
        
        ## 📋 Wymagania dla danych:
        - Format CSV
        - Co najmniej 10 wierszy danych
        - Kolumny numeryczne lub kategoryczne
        - Maksymalnie 70% wartości brakujących w kolumnach
        
        """)

if __name__ == "__main__":
    # Streamlit automatycznie użyje PORT z --server.port w run command
    # PORT jest ustawiany przez zmienną środowiskową $PORT w App Platform
    main()