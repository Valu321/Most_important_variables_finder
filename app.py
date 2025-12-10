import streamlit as st
import pandas as pd
import os
import warnings
from typing import Tuple, Optional, Any

# Imports for visualization
import plotly.express as px

# PyCaret imports with aliases to prevent namespace collision
from pycaret import classification as pc_clf
from pycaret import regression as pc_reg

# OpenAI & Observability
from dotenv import load_dotenv
from openai import OpenAI
from langfuse.decorators import langfuse_context, observe
from langfuse.openai import openai as langfuse_openai

# Suppress warnings
warnings.filterwarnings('ignore')

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Analiza Najważniejszych Cech (Powered by GPT-4o-mini)",
    page_icon="📊",
    layout="wide"
)
load_dotenv()

# --- SERVICES ---

class ConfigService:
    """Obsługuje konfigurację środowiska i klucze API."""
    
    @staticmethod
    def get_langfuse_config() -> bool:
        """Sprawdza i konfiguruje Langfuse, jeśli dane uwierzytelniające są obecne."""
        try:
            public_key = os.getenv('LANGFUSE_PUBLIC_KEY')
            secret_key = os.getenv('LANGFUSE_SECRET_KEY')
            host = os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')
            
            if public_key and secret_key:
                langfuse_openai.langfuse.public_key = public_key
                langfuse_openai.langfuse.secret_key = secret_key
                langfuse_openai.langfuse.host = host
                return True
            return False
        except Exception:
            return False

    @staticmethod
    def get_openai_client(api_key: Optional[str], langfuse_enabled: bool):
        """Zwraca odpowiedniego klienta OpenAI (z wrapperem Langfuse lub bez)."""
        if not api_key:
            return None
            
        if langfuse_enabled:
            langfuse_openai.api_key = api_key
            return langfuse_openai
        else:
            return OpenAI(api_key=api_key)

class AnalysisService:
    """Obsługuje logikę analizy danych przy użyciu PyCaret."""

    @staticmethod
    def preprocess_data(data: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
        """
        Zaawansowany pipeline czyszczący dane, dedykowany m.in. wynikom sportowym.
        1. Obsługuje separatory (średniki).
        2. Zamienia znaczniki DNS/DNF na NaN.
        3. Konwertuje czasy (HH:MM:SS) na sekundy.
        4. Naprawia kolumny numeryczne 'zanieczyszczone' tekstem.
        """
        data = data.copy()
        logs = []

        # 1. Obsługa wartości specjalnych (DNS, DNF, etc.)
        special_markers = ['DNS', 'DNF', 'DSQ', 'NM', 'DQ', 'dns', 'dnf']
        # Zamień na NaN, ale tylko w kolumnach, które mogą być numeryczne
        data.replace(special_markers, pd.NA, inplace=True)
        
        # 2. Inteligentna konwersja kolumn
        for col in data.columns:
            if data[col].dtype == 'object':
                sample = data[col].dropna().astype(str)
                if len(sample) == 0:
                    continue

                # A. Konwersja Czasu (HH:MM:SS lub MM:SS) na sekundy
                # Sprawdzamy czy większość wartości pasuje do formatu czasu
                is_time = sample.str.match(r'^(\d{1,2}:)?\d{1,2}:\d{2}(\.\d+)?$').mean() > 0.5
                
                if is_time:
                    try:
                        # pd.to_timedelta wymaga formatu HH:MM:SS, jeśli jest MM:SS dodajemy 00:
                        temp_col = pd.to_timedelta(data[col].astype(str), errors='coerce')
                        
                        # Jeśli to_timedelta zwróciło dużo NaT, a regex pasował, może format był dziwny
                        # Ale dla standardowych formatów zadziała.
                        if temp_col.notna().sum() > 0.1 * len(data):
                            data[f"{col} (sec)"] = temp_col.dt.total_seconds()
                            # Opcjonalnie: Usuwamy oryginalną kolumnę tekstową lub zostawiamy
                            # PyCaret lepiej poradzi sobie z (sec).
                            # Zastępujemy oryginał dla uproszczenia wyboru targetu
                            data[col] = temp_col.dt.total_seconds()
                            logs.append(f"⏱️ Zkonwertowano czas '{col}' na sekundy.")
                            continue
                    except Exception:
                        pass

                # B. Forsowanie typów numerycznych (np. gdy kolumna ma liczby i 'DNS')
                try:
                    numeric_col = pd.to_numeric(data[col], errors='coerce')
                    # Jeśli po konwersji mamy > 50% liczb (a reszta to np. NaN po DNS), to jest to kolumna liczbowa
                    if numeric_col.notna().sum() > 0.5 * len(data):
                        data[col] = numeric_col
                        logs.append(f"🔢 Naprawiono typ numeryczny w kolumnie '{col}'.")
                except:
                    pass

        return data, "\n\n".join(logs) if logs else "Brak specjalnych transformacji."

    @staticmethod
    def determine_problem_type(data: pd.DataFrame, target_column: str) -> str:
        """Heurystycznie określa, czy problem to klasyfikacja czy regresja."""
        target_data = data[target_column]
        
        # Sprawdzenie klasyfikacji: mała liczba unikalnych wartości względem rozmiaru danych
        unique_values = target_data.nunique(dropna=True)
        total_values = len(target_data)
        
        if total_values > 0 and unique_values / total_values < 0.2:
            return "klasyfikacja"

        # Sprawdzenie regresji: dane głównie numeryczne
        numeric_data = pd.to_numeric(target_data, errors='coerce')
        non_numeric_ratio = numeric_data.isna().mean()
        
        if non_numeric_ratio < 0.1:
            return "regresja"

        return "klasyfikacja" # Domyślny fallback

    @staticmethod
    def run_analysis(data: pd.DataFrame, target_column: str, problem_type: str) -> Tuple[Optional[pd.DataFrame], Any]:
        """
        Uruchamia potok analizy PyCaret.
        """
        # 1. Podstawowe czyszczenie danych (wiersze i kolumny z brakami)
        # Zwiększamy tolerancję na braki danych w kolumnach, bo po 'preprocess_data' możemy mieć NaN zamiast DNS
        data_clean = data.dropna(thresh=len(data) * 0.6, axis=1) 
        data_clean = data_clean.dropna(subset=[target_column]) # Target musi być obecny
        
        # Opcjonalnie: imputacja prostym usunięciem wierszy dla szybkości demo
        data_clean = data_clean.dropna()
        
        if target_column not in data_clean.columns:
            return None, f"Kolumna docelowa '{target_column}' została usunięta (zbyt wiele braków danych)."
            
        # --- FIX: Usunięcie rzadkich klas (błąd PyCaret) ---
        if problem_type == "klasyfikacja":
            class_counts = data_clean[target_column].value_counts()
            rare_classes = class_counts[class_counts < 2].index.tolist()
            
            if rare_classes:
                st.warning(f"⚠️ Usunięto wiersze z rzadkimi klasami (występującymi tylko raz): {rare_classes}")
                data_clean = data_clean[~data_clean[target_column].isin(rare_classes)]
        # ---------------------------------------------------

        if len(data_clean) < 10:
            return None, "Za mało danych po czyszczeniu (wymagane min. 10 wierszy i min. 2 przykłady na klasę)."

        # 2. Wybór modułu PyCaret
        module = pc_clf if problem_type == "klasyfikacja" else pc_reg

        try:
            # 3. Konfiguracja eksperymentu
            module.setup(
                data=data_clean,
                target=target_column,
                session_id=123,
                verbose=False,
                html=False,
                imputation_type='simple' # Dodatkowe zabezpieczenie
            )
            
            # 4. Trenowanie i porównanie modeli
            best_model = module.compare_models(
                include=['rf', 'xgboost', 'lightgbm'], 
                verbose=False
            )
            
            # 5. Ekstrakcja ważności cech
            X_transformed = module.get_config('X_train_transformed')
            feature_names = X_transformed.columns
            
            importances = [0] * len(feature_names)
            if hasattr(best_model, 'feature_importances_'):
                 importances = best_model.feature_importances_
            
            if len(feature_names) != len(importances):
                return None, f"Niezgodność wymiarów cech ({len(feature_names)}) i ważności ({len(importances)})."

            importance_df = pd.DataFrame({
                'Feature': feature_names,
                'Importance': importances
            }).sort_values('Importance', ascending=False)
            
            return importance_df, best_model

        except Exception as e:
            return None, f"Błąd wewnętrzny PyCaret: {str(e)}"

class OpenAIService:
    """Obsługuje generowanie tekstu przy użyciu OpenAI."""
    
    @staticmethod
    def generate_description(
        client: Any,
        importance_df: pd.DataFrame, 
        problem_type: str, 
        target_column: str, 
        data_info: str,
        langfuse_enabled: bool
    ) -> str:
        
        if client is None:
            top_feature = importance_df.iloc[0]
            pct = (top_feature['Importance'] / importance_df['Importance'].sum()) * 100
            return f"""
            ## ⚠️ Wymagany klucz API
            
            Aby wygenerować opis biznesowy, wprowadź swój klucz OpenAI API w panelu bocznym.
            
            **Najważniejsza cecha (wykryta):** {top_feature['Feature']} ({pct:.1f}%)
            """

        try:
            # Przygotowanie promptu
            top_features = importance_df.head(10)
            features_text = "\n".join([
                f"{i+1}. {row['Feature']}: {row['Importance']:.4f}" 
                for i, (_, row) in enumerate(top_features.iterrows())
            ])
            
            prompt = f"""
            Jesteś ekspertem Data Science. Przeanalizuj wyniki modelu ML.
            
            KONTEKST:
            - Problem: {problem_type}
            - Cel: Przewidywanie kolumny '{target_column}'
            - Dane: {data_info}
            
            WYNIKI (Ważność cech z modelu):
            {features_text}
            
            ZADANIE:
            Stwórz zwięzły raport biznesowy w Markdown.
            1. Zidentyfikuj kluczowe czynniki (drivers).
            2. Postaw hipotezy dlaczego te cechy są ważne.
            3. Zasugeruj konkretne działania biznesowe lub wnioski analityczne.
            
            Styl: Profesjonalny, zwięzły, konkretny.
            """

            # Langfuse Trace
            if langfuse_enabled:
                langfuse_context.update_current_trace(
                    name="generate_analysis_desc",
                    metadata={
                        "problem": problem_type, 
                        "target": target_column,
                        "model": "gpt-4o-mini"
                    }
                )

            # Wywołanie API - GPT-4o-mini
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Jesteś pomocnym analitykiem danych. Odpowiadasz w języku polskim."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            return f"## 🤖 Analiza AI (GPT-4o-mini)\n\n{response.choices[0].message.content}"

        except Exception as e:
            return f"## ❌ Błąd generowania opisu\n\n{str(e)}"

# --- UI COMPONENTS ---

def render_sidebar():
    st.sidebar.header("📁 Dane i Konfiguracja")
    
    uploaded_file = st.sidebar.file_uploader(
        "Wgraj plik CSV", 
        type=['csv'],
        help="Plik musi zawierać nagłówki kolumn."
    )
    
    # 🛡️ ZABEZPIECZENIE: Limit wielkości pliku (10MB)
    if uploaded_file is not None:
        if uploaded_file.size > 10 * 1024 * 1024:
            st.sidebar.error("🚨 Plik jest za duży! Maksymalnie 10MB.")
            uploaded_file = None # Blokujemy dalsze przetwarzanie

    st.sidebar.divider()
    
    # 🛡️ ZABEZPIECZENIE: Informacja o prywatności
    st.sidebar.info(
        "🔒 **Prywatność i RODO**\n\n"
        "Aplikacja wykorzystuje OpenAI API do generowania opisów. "
        "Nazwy kolumn Twoich danych będą przesyłane do zewnętrznego dostawcy. "
        "**Nie wgrywaj plików zawierających dane poufne lub RODO.**"
    )
    
    st.sidebar.header("🔑 API")
    
    # 🛡️ ZABEZPIECZENIE: Model SaaS (Użytkownik podaje klucz)
    api_key = st.sidebar.text_input(
        "Twój klucz OpenAI API",
        type="password",
        value=os.getenv("OPENAI_API_KEY", ""),
        help="Wymagany do analizy AI. Wprowadź swój klucz, aby korzystać z GPT-4o-mini."
    )
    
    return uploaded_file, api_key

@st.cache_data
def load_data(file) -> pd.DataFrame:
    # Inteligentne ładowanie: próba wykrycia separatora
    try:
        # engine='python' pozwala na autodetekcję separatora
        return pd.read_csv(file, sep=None, engine='python')
    except:
        # Fallback do domyślnego
        file.seek(0)
        return pd.read_csv(file)

def render_metrics(data: pd.DataFrame):
    col1, col2, col3 = st.columns(3)
    col1.metric("Liczba wierszy", len(data))
    col2.metric("Liczba kolumn", len(data.columns))
    col3.metric("Brakujące dane", f"{data.isna().sum().sum()}")

def main():
    # 1. Inicjalizacja
    langfuse_active = ConfigService.get_langfuse_config()
    
    st.title("📊 Analiza Ważności Cech")
    st.markdown("Aplikacja automatycznie trenuje modele ML i wyjaśnia wyniki przy użyciu **GPT-4o-mini**.")
    
    # 2. Panel boczny
    uploaded_file, user_api_key = render_sidebar()
    
    # 3. Główna logika
    if uploaded_file:
        try:
            df_raw = load_data(uploaded_file)
            
            # === NOWY KROK: PREPROCESSING ===
            # Wykonujemy czyszczenie zaraz po załadowaniu
            with st.spinner("🧹 Oczyszczanie danych (konwersja czasu, obsługa błędów)..."):
                df, cleaning_logs = AnalysisService.preprocess_data(df_raw)
            
            # Wyświetlenie logów czyszczenia w expanderze
            with st.expander("🛠️ Logi czyszczenia danych (Kliknij, aby zobaczyć szczegóły)"):
                st.text(cleaning_logs)
            # ===============================

            # Podgląd danych
            with st.expander("🔍 Podgląd danych (po oczyszczeniu)", expanded=True):
                render_metrics(df)
                st.dataframe(df.head(5), use_container_width=True)
            
            # Wybór celu
            st.divider()
            col_sel, col_btn = st.columns([3, 1])
            with col_sel:
                target_col = st.selectbox("Wybierz kolumnę docelową (Target):", df.columns)
            
            with col_btn:
                st.write("") # Odstęp
                st.write("") # Odstęp
                start_btn = st.button("🚀 Rozpocznij Analizę", type="primary", use_container_width=True)
            
            if start_btn:
                with st.spinner("⚙️ Przetwarzanie danych i trenowanie modeli..."):
                    # Analiza
                    problem_type = AnalysisService.determine_problem_type(df, target_col)
                    st.info(f"Wykryty typ problemu: **{problem_type.upper()}**")
                    
                    imp_df, model_or_err = AnalysisService.run_analysis(df, target_col, problem_type)
                    
                    if imp_df is not None:
                        # Wizualizacja
                        col_chart, col_desc = st.columns([1, 1])
                        
                        with col_chart:
                            st.subheader("📈 Wykres Ważności")
                            fig = px.bar(
                                imp_df.head(15),
                                x='Importance',
                                y='Feature',
                                orientation='h',
                                color='Importance',
                                color_continuous_scale='Bluered_r'
                            )
                            fig.update_layout(yaxis={'categoryorder':'total ascending'})
                            st.plotly_chart(fig, use_container_width=True)
                            
                            with st.expander("Pokaż tabelę danych"):
                                st.dataframe(imp_df, use_container_width=True)

                        with col_desc:
                            # Opis AI
                            client = ConfigService.get_openai_client(user_api_key, langfuse_active)
                            data_info = f"Wierszy: {len(df)}, Kolumn: {len(df.columns)}"
                            
                            desc = OpenAIService.generate_description(
                                client, imp_df, problem_type, target_col, data_info, langfuse_active
                            )
                            st.markdown(desc)
                            
                    else:
                        st.error(f"Błąd analizy: {model_or_err}")

        except Exception as e:
            st.error(f"Nie udało się przetworzyć pliku: {str(e)}")
    else:
        st.info("👈 Wgraj plik CSV w panelu bocznym, aby rozpocząć.")

if __name__ == "__main__":
    main()