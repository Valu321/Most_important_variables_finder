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

# Try importing LangfuseOpenAI safely
try:
    from langfuse.openai import OpenAI as LangfuseOpenAI
    from langfuse.decorators import langfuse_context, observe
    LANGFUSE_AVAILABLE = True
except ImportError:
    LangfuseOpenAI = None
    langfuse_context = None
    LANGFUSE_AVAILABLE = False

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
        """Sprawdza, czy konfiguracja Langfuse jest poprawna."""
        if not LANGFUSE_AVAILABLE:
            return False
            
        public_key = os.getenv('LANGFUSE_PUBLIC_KEY')
        secret_key = os.getenv('LANGFUSE_SECRET_KEY')
        
        # Langfuse automatycznie pobiera zmienne środowiskowe, 
        # więc wystarczy sprawdzić czy istnieją.
        if public_key and secret_key:
            return True
        return False

    @staticmethod
    def get_openai_client(api_key: Optional[str], langfuse_enabled: bool):
        """Zwraca odpowiednią instancję klienta OpenAI."""
        if not api_key:
            return None
            
        if langfuse_enabled and LANGFUSE_AVAILABLE:
            # Używamy klasy wrapper Langfuse, która zachowuje się jak standardowy klient OpenAI
            return LangfuseOpenAI(api_key=api_key)
        else:
            # Standardowy klient OpenAI
            return OpenAI(api_key=api_key)

class AnalysisService:
    """Obsługuje logikę analizy danych przy użyciu PyCaret."""

    @staticmethod
    def preprocess_data(data: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
        """
        Zaawansowany pipeline czyszczący dane.
        """
        data = data.copy()
        logs = []

        # 1. Obsługa wartości specjalnych (DNS, DNF, etc.)
        special_markers = ['DNS', 'DNF', 'DSQ', 'NM', 'DQ', 'dns', 'dnf']
        data.replace(special_markers, pd.NA, inplace=True)
        
        # 2. Inteligentna konwersja kolumn
        for col in data.columns:
            if data[col].dtype == 'object':
                sample = data[col].dropna().astype(str)
                if len(sample) == 0:
                    continue

                # A. Konwersja Czasu (HH:MM:SS lub MM:SS) na sekundy
                is_time = sample.str.match(r'^(\d{1,2}:)?\d{1,2}:\d{2}(\.\d+)?$').mean() > 0.5
                
                if is_time:
                    try:
                        temp_col = pd.to_timedelta(data[col].astype(str), errors='coerce')
                        if temp_col.notna().sum() > 0.1 * len(data):
                            data[f"{col} (sec)"] = temp_col.dt.total_seconds()
                            data[col] = temp_col.dt.total_seconds()
                            logs.append(f"⏱️ Zkonwertowano czas '{col}' na sekundy.")
                            continue
                    except Exception:
                        pass

                # B. Forsowanie typów numerycznych
                try:
                    numeric_col = pd.to_numeric(data[col], errors='coerce')
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
        
        unique_values = target_data.nunique(dropna=True)
        total_values = len(target_data)
        
        if total_values > 0 and unique_values / total_values < 0.2:
            return "klasyfikacja"

        numeric_data = pd.to_numeric(target_data, errors='coerce')
        non_numeric_ratio = numeric_data.isna().mean()
        
        if non_numeric_ratio < 0.1:
            return "regresja"

        return "klasyfikacja"

    @staticmethod
    def run_analysis(data: pd.DataFrame, target_column: str, problem_type: str) -> Tuple[Optional[pd.DataFrame], Any]:
        """Uruchamia potok analizy PyCaret."""
        
        # 1. Podstawowe czyszczenie
        data_clean = data.dropna(thresh=len(data) * 0.6, axis=1) 
        data_clean = data_clean.dropna(subset=[target_column])
        data_clean = data_clean.dropna() # Szybka imputacja przez usunięcie
        
        if target_column not in data_clean.columns:
            return None, f"Kolumna docelowa '{target_column}' została usunięta."
            
        # --- FIX: Usunięcie rzadkich klas ---
        if problem_type == "klasyfikacja":
            class_counts = data_clean[target_column].value_counts()
            rare_classes = class_counts[class_counts < 2].index.tolist()
            if rare_classes:
                st.warning(f"⚠️ Usunięto rzadkie klasy: {rare_classes}")
                data_clean = data_clean[~data_clean[target_column].isin(rare_classes)]
        # ------------------------------------

        if len(data_clean) < 10:
            return None, "Za mało danych po czyszczeniu (min. 10 wierszy)."

        module = pc_clf if problem_type == "klasyfikacja" else pc_reg

        try:
            module.setup(
                data=data_clean,
                target=target_column,
                session_id=123,
                verbose=False,
                html=False,
                imputation_type='simple'
            )
            
            best_model = module.compare_models(
                include=['rf', 'xgboost', 'lightgbm'], 
                verbose=False
            )
            
            X_transformed = module.get_config('X_train_transformed')
            feature_names = X_transformed.columns
            
            importances = [0] * len(feature_names)
            if hasattr(best_model, 'feature_importances_'):
                 importances = best_model.feature_importances_
            
            if len(feature_names) != len(importances):
                # Fallback w przypadku niedopasowania (np. pipeline przetworzył cechy inaczej)
                return None, "Niezgodność wymiarów cech."

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
            **Najważniejsza cecha:** {top_feature['Feature']} ({pct:.1f}%)
            """

        try:
            top_features = importance_df.head(10)
            features_text = "\n".join([
                f"{i+1}. {row['Feature']}: {row['Importance']:.4f}" 
                for i, (_, row) in enumerate(top_features.iterrows())
            ])
            
            prompt = f"""
            Jesteś ekspertem Data Science. Przeanalizuj wyniki modelu ML.
            KONTEKST: Problem: {problem_type}, Cel: '{target_column}', Dane: {data_info}
            WYNIKI:
            {features_text}
            ZADANIE: Krótki raport biznesowy (Markdown). Kluczowe czynniki, hipotezy, wnioski.
            """

            # Langfuse Trace
            if langfuse_enabled and LANGFUSE_AVAILABLE and langfuse_context:
                langfuse_context.update_current_trace(
                    name="generate_analysis_desc",
                    metadata={"problem": problem_type, "target": target_column}
                )

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Jesteś pomocnym analitykiem danych."},
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
    uploaded_file = st.sidebar.file_uploader("Wgraj plik CSV", type=['csv'])
    
    if uploaded_file is not None and uploaded_file.size > 10 * 1024 * 1024:
        st.sidebar.error("🚨 Plik jest za duży! Maks. 10MB.")
        uploaded_file = None

    st.sidebar.divider()
    st.sidebar.info("🔒 Dane są wysyłane do OpenAI w celu analizy.")
    st.sidebar.header("🔑 API")
    
    api_key = st.sidebar.text_input(
        "Twój klucz OpenAI API",
        type="password",
        value=os.getenv("OPENAI_API_KEY", "")
    )
    
    return uploaded_file, api_key

@st.cache_data
def load_data(file) -> pd.DataFrame:
    try:
        return pd.read_csv(file, sep=None, engine='python')
    except:
        file.seek(0)
        return pd.read_csv(file)

def render_metrics(data: pd.DataFrame):
    col1, col2, col3 = st.columns(3)
    col1.metric("Liczba wierszy", len(data))
    col2.metric("Liczba kolumn", len(data.columns))
    col3.metric("Brakujące dane", f"{data.isna().sum().sum()}")

def main():
    langfuse_active = ConfigService.get_langfuse_config()
    
    st.title("📊 Analiza Ważności Cech")
    st.markdown("Automatyczna analiza ML + GPT-4o-mini.")
    
    uploaded_file, user_api_key = render_sidebar()
    
    if uploaded_file:
        try:
            df_raw = load_data(uploaded_file)
            
            with st.spinner("🧹 Przetwarzanie wstępne..."):
                df, cleaning_logs = AnalysisService.preprocess_data(df_raw)
            
            with st.expander("🛠️ Logi czyszczenia"):
                st.text(cleaning_logs)

            with st.expander("🔍 Podgląd danych", expanded=True):
                render_metrics(df)
                st.dataframe(df.head(5), use_container_width=True)
            
            st.divider()
            col_sel, col_btn = st.columns([3, 1])
            with col_sel:
                target_col = st.selectbox("Cel (Target):", df.columns)
            
            with col_btn:
                st.write("")
                st.write("")
                start_btn = st.button("🚀 Start", type="primary", use_container_width=True)
            
            if start_btn:
                with st.spinner("⚙️ Trenowanie modelu..."):
                    problem_type = AnalysisService.determine_problem_type(df, target_col)
                    st.info(f"Typ problemu: **{problem_type.upper()}**")
                    
                    imp_df, model_or_err = AnalysisService.run_analysis(df, target_col, problem_type)
                    
                    if imp_df is not None:
                        col_chart, col_desc = st.columns([1, 1])
                        with col_chart:
                            st.subheader("📈 Wykres")
                            fig = px.bar(imp_df.head(15), x='Importance', y='Feature', orientation='h', color='Importance')
                            fig.update_layout(yaxis={'categoryorder':'total ascending'})
                            st.plotly_chart(fig, use_container_width=True)
                            
                        with col_desc:
                            client = ConfigService.get_openai_client(user_api_key, langfuse_active)
                            data_info = f"Wierszy: {len(df)}"
                            desc = OpenAIService.generate_description(client, imp_df, problem_type, target_col, data_info, langfuse_active)
                            st.markdown(desc)
                    else:
                        st.error(f"Błąd: {model_or_err}")

        except Exception as e:
            st.error(f"Błąd pliku: {str(e)}")
    else:
        st.info("👈 Wgraj plik CSV.")

if __name__ == "__main__":
    main()