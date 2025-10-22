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
import warnings
warnings.filterwarnings('ignore')

# Załaduj zmienne środowiskowe
load_dotenv()

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
    """Określa czy problem to klasyfikacja czy regresja"""
    target_data = data[target_column]
    
    # Sprawdź czy kolumna docelowa to liczby całkowite z małą liczbą unikalnych wartości
    if target_data.dtype in ['int64', 'int32', 'object']:
        unique_values = target_data.nunique()
        total_values = len(target_data)
        
        # Jeśli mniej niż 20% unikalnych wartości, traktuj jako klasyfikację
        if unique_values / total_values < 0.2:
            return "klasyfikacja"
    
    # Sprawdź czy można przekonwertować na liczby
    try:
        numeric_data = pd.to_numeric(target_data, errors='coerce')
        if numeric_data.isna().sum() / len(numeric_data) < 0.1:  # Mniej niż 10% wartości nie-numerycznych
            return "regresja"
    except:
        pass
    
    return "klasyfikacja"  # Domyślnie klasyfikacja

# Funkcja do analizy ważności cech
def analyze_feature_importance(data, target_column, problem_type):
    """Analizuje ważność cech używając PyCaret"""
    
    # Przygotowanie danych
    feature_columns = [col for col in data.columns if col != target_column]
    
    # Usuń kolumny z dużą liczbą wartości brakujących
    data_clean = data.dropna(thresh=len(data) * 0.7, axis=1)
    
    # Usuń wiersze z wartościami brakującymi
    data_clean = data_clean.dropna()
    
    if len(data_clean) < 10:
        return None, "Za mało danych po czyszczeniu"
    
    try:
        if problem_type == "klasyfikacja":
            # Konfiguracja PyCaret dla klasyfikacji
            clf = setup(
                data_clean,
                target=target_column,
                session_id=123
            )
            
            # Porównanie modeli
            best_model = compare_models(include=['rf', 'xgboost', 'lightgbm'], verbose=False)
            
            # Analiza ważności cech
            importance_df = pd.DataFrame({
                'Feature': feature_columns,
                'Importance': best_model.feature_importances_ if hasattr(best_model, 'feature_importances_') else [0] * len(feature_columns)
            })
            
        else:  # regresja
            # Konfiguracja PyCaret dla regresji
            reg = setup(
                data_clean,
                target=target_column,
                session_id=123
            )
            
            # Porównanie modeli
            best_model = compare_models(include=['rf', 'xgboost', 'lightgbm'], verbose=False)
            
            # Analiza ważności cech
            importance_df = pd.DataFrame({
                'Feature': feature_columns,
                'Importance': best_model.feature_importances_ if hasattr(best_model, 'feature_importances_') else [0] * len(feature_columns)
            })
        
        # Sortuj według ważności
        importance_df = importance_df.sort_values('Importance', ascending=False)
        
        return importance_df, best_model
        
    except Exception as e:
        return None, f"Błąd podczas analizy: {str(e)}"

# Funkcja do generowania opisu przez OpenAI
def generate_description_with_gpt(importance_df, problem_type, target_column, data_info):
    """Generuje opis słowny wyników używając OpenAI API"""
    
    if importance_df is None or len(importance_df) == 0:
        return "Nie udało się wygenerować opisu z powodu błędów w analizie."
    
    # Sprawdź czy klucz API jest dostępny
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return """
## ⚠️ Brak klucza API

Aby wygenerować opis przez ChatGPT, dodaj klucz OpenAI API do pliku `.env`:

```
OPENAI_API_KEY=your_api_key_here
```

**Tymczasowy opis:**
Najważniejsze cechy zostały zidentyfikowane w tabeli powyżej. 
Najwyższa ważność: **{0}** ({1:.1f}%).
        """.format(
            importance_df.iloc[0]['Feature'],
            (importance_df.iloc[0]['Importance'] / importance_df['Importance'].sum()) * 100
        )
    
    try:
        # Konfiguracja OpenAI - nowy interfejs
        from openai import OpenAI
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
        
        # Wywołanie API - nowy interfejs
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
    
    if uploaded_file is not None:
        try:
            # Wczytanie danych
            data = pd.read_csv(uploaded_file)
            
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
                            x='Ważność',
                            y='Cecha',
                            orientation='h',
                            title="Top 10 najważniejszych cech",
                            color='ważność',
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
                            description = generate_description_with_gpt(importance_df, problem_type, target_column, data_info)
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
        
        ## 🔑 Konfiguracja ChatGPT:
        Aby korzystać z automatycznego generowania opisów, dodaj klucz OpenAI API do pliku `.env`:
        ```
        OPENAI_API_KEY=your_api_key_here
        ```
        """)

if __name__ == "__main__":
    main()
