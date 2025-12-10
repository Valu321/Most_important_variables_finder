import streamlit as st
import pandas as pd
import os
import warnings
import time
import threading
import gc
from typing import Tuple, Optional, Any, List

# Imports for visualization
import plotly.express as px

# System monitoring imports
try:
    import psutil
except ImportError:
    psutil = None

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
    layout="wide",
    initial_sidebar_state="expanded"
)
load_dotenv()

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    /* Poprawka dla kart metryk - kompatybilność z trybem ciemnym */
    .stMetric {
        background-color: rgba(255, 255, 255, 0.05); /* Półprzezroczyste tło */
        padding: 15px;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    /* Usunięto wymuszenie jasnego tła dla sidebaru, aby pasował do motywu */
    /* [data-testid="stSidebar"] {
        background-color: #f8f9fa; 
    } */
    h1, h2, h3 {
        font-family: 'Helvetica Neue', sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SERVICES ---

class MemoryMonitor:
    """
    Serwis do monitorowania zużycia pamięci w tle podczas ciężkich obliczeń.
    Pozwala uniknąć 'cichego' restartu aplikacji na DigitalOcean przez OOM Killer.
    """
    def __init__(self, chart_placeholder=None, text_placeholder=None):
        self.chart_placeholder = chart_placeholder if chart_placeholder else st.empty()
        self.text_placeholder = text_placeholder if text_placeholder else st.empty()
        self.history = []
        self.running = False
        self.thread = None

    def get_stats(self):
        if psutil is None:
            return 0, 0
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        rss_mb = mem_info.rss / 1024 / 1024
        sys_mem = psutil.virtual_memory()
        return rss_mb, sys_mem.percent

    def update_ui(self):
        rss_mb, sys_percent = self.get_stats()
        self.history.append(rss_mb)
        
        # Aktualizacja UI Streamlit (w trybie thread-safe 'best effort')
        try:
            self.text_placeholder.markdown(f"""
            **Status Pamięci (Live):**
            - RAM Aplikacji: `{rss_mb:.2f} MB`
            - RAM Systemu: `{sys_percent}%`
            """)
            self.chart_placeholder.line_chart(self.history, height=150)
        except Exception:
            pass 

    def start_background_monitoring(self, interval=1.0):
        """Uruchamia monitorowanie w tle."""
        if psutil is None:
            # Nie wyświetlamy ostrzeżenia, aby nie zaśmiecać UI, jeśli nie jest to krytyczne
            return

        self.running = True
        self.history = [] # Reset historii
        self.thread = threading.Thread(target=self._monitor_loop, args=(interval,), daemon=True)
        self.thread.start()

    def stop_background_monitoring(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)

    def _monitor_loop(self, interval):
        while self.running:
            self.update_ui()
            time.sleep(interval)

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
        
        # 1. Sprawdzenie czy dane są numeryczne
        numeric_data = pd.to_numeric(target_data, errors='coerce')
        is_mostly_numeric = numeric_data.isna().mean() < 0.1

        # 2. Jeśli dane są numeryczne i mają dużo unikalnych wartości (np. > 20), to raczej regresja
        if is_mostly_numeric and unique_values > 20:
            return "regresja"
        
        # 3. Jeśli mało unikalnych wartości (np. mniej niż 20% danych), to klasyfikacja
        if total_values > 0 and unique_values / total_values < 0.2:
            return "klasyfikacja"

        # Fallback: jeśli numeryczne -> regresja, w przeciwnym razie klasyfikacja
        if is_mostly_numeric:
            return "regresja"

        return "klasyfikacja"

    @staticmethod
    def run_analysis(data: pd.DataFrame, target_column: str, problem_type: str) -> Tuple[Optional[pd.DataFrame], Any]:
        """Uruchamia potok analizy PyCaret."""
        
        # 1. Podstawowe czyszczenie
        data_clean = data.dropna(thresh=len(data) * 0.6, axis=1) 
        data_clean = data_clean.dropna(subset=[target_column])
        
        # Usuwamy wiersze gdzie target nie jest znany (dla pewności)
        if problem_type == "regresja":
             data_clean = data_clean[pd.to_numeric(data_clean[target_column], errors='coerce').notna()]
        
        data_clean = data_clean.dropna() # Szybka imputacja przez usunięcie
        
        if target_column not in data_clean.columns:
            return None, f"Kolumna docelowa '{target_column}' została usunięta."
            
        # --- SAFETY GUARD: Inteligentna obsługa rzadkich klas ---
        # Jeśli PyCaret wykryje rzadkie klasy w problemie, który wygląda na klasyfikację,
        # ale jest to np. ranking (1, 2, 3...), usunięcie klas wyczyści cały dataset.
        if problem_type == "klasyfikacja":
            class_counts = data_clean[target_column].value_counts()
            rare_classes = class_counts[class_counts < 2].index.tolist()
            
            if rare_classes:
                rows_before = len(data_clean)
                rows_after_filter = len(data_clean[~data_clean[target_column].isin(rare_classes)])
                
                # Jeśli usunięcie rzadkich klas kasuje więcej niż 30% danych lub zostawia mniej niż 10 wierszy
                if rows_after_filter < 10 or (rows_after_filter / rows_before) < 0.7:
                    st.warning(f"⚠️ Wykryto bardzo dużą liczbę unikalnych wartości dla Klasyfikacji (np. ranking). Przełączam tryb na **Regresję**, aby nie tracić danych.")
                    problem_type = "regresja"
                else:
                    st.warning(f"⚠️ Usunięto rzadkie klasy (występujące tylko raz): {len(rare_classes)} przypadków.")
                    data_clean = data_clean[~data_clean[target_column].isin(rare_classes)]
        # --------------------------------------------------------

        if len(data_clean) < 10:
            return None, f"Za mało danych po czyszczeniu (zostało {len(data_clean)} wierszy, wymagane min. 10)."

        # Wybór modułu po ewentualnej zmianie problem_type przez Safety Guard
        module = pc_clf if problem_type == "klasyfikacja" else pc_reg

        try:
            # Wymuszamy GC przed startem, żeby zwolnić pamięć po preprocessing
            gc.collect()
            
            module.setup(
                data=data_clean,
                target=target_column,
                session_id=123,
                verbose=False,
                html=False,
                imputation_type='simple',
                n_jobs=1 # Ograniczamy zużycie wątków na małych maszynach
            )
            
            # Trenowanie lekkich modeli dla szybkości
            best_model = module.compare_models(
                include=['rf', 'dt', 'lightgbm'], 
                verbose=False
            )
            
            if best_model is None:
                return None, "Nie udało się wytrenować żadnego modelu (sprawdź jakość danych)."

            X_transformed = module.get_config('X_train_transformed')
            feature_names = X_transformed.columns
            
            importances = [0] * len(feature_names)
            if hasattr(best_model, 'feature_importances_'):
                 importances = best_model.feature_importances_
            
            # Fallback dla modeli bez feature_importances_ (np. liniowe w regresji)
            elif hasattr(best_model, 'coef_'):
                 importances = abs(best_model.coef_)
                 if len(importances.shape) > 1: # Dla multiclass
                     importances = importances.mean(axis=0)

            if len(feature_names) != len(importances):
                # Fallback w przypadku niedopasowania (rzadki przypadek preprocessingu PyCaret)
                # Zwracamy puste, ale poprawne strukturalnie
                return pd.DataFrame({'Feature': feature_names[:len(importances)], 'Importance': importances}), best_model

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

def render_sidebar(columns: List[str] = None):
    st.sidebar.header("📁 Dane")
    uploaded_file = st.sidebar.file_uploader("Wgraj plik CSV (maks. 10MB)", type=['csv'])
    
    if uploaded_file is not None and uploaded_file.size > 10 * 1024 * 1024:
        st.sidebar.error("🚨 Plik jest za duży! Maks. 10MB.")
        uploaded_file = None

    st.sidebar.divider()
    
    # Sekcja konfiguracji analizy (widoczna tylko gdy plik wgrany)
    target_col = None
    problem_type_mode = "Auto"
    
    if columns:
        st.sidebar.header("⚙️ Konfiguracja Analizy")
        target_col = st.sidebar.selectbox("🎯 Kolumna Celu (Target):", columns)
        
        mode_options = {
            "Automatyczny (Zalecane)": "Auto",
            "Klasyfikacja (Ręczny)": "klasyfikacja",
            "Regresja (Ręczny)": "regresja"
        }
        
        selected_mode_label = st.sidebar.radio(
            "Tryb modelu:",
            list(mode_options.keys()),
            help="Wybierz 'Auto', aby system sam wykrył typ problemu, lub wymuś konkretny algorytm."
        )
        problem_type_mode = mode_options[selected_mode_label]
        
        st.sidebar.divider()

    st.sidebar.warning(
        "Aplikacja wykorzystuje OpenAI API. Nazwy kolumn są przesyłane do zewnętrznego dostawcy. "
        "Nie wgrywaj plików z danymi poufnymi (RODO)."
    )
    
    st.sidebar.header("🔑 API Key")
    api_key = st.sidebar.text_input(
        "Klucz OpenAI API",
        type="password",
        value=os.getenv("OPENAI_API_KEY", ""),
        help="Wymagany do generowania opisów słownych."
    )
    
    return uploaded_file, api_key, target_col, problem_type_mode

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
    st.markdown("Automatyczna analiza ML wspierana przez AI. Wgraj dane, wybierz cel i poznaj kluczowe czynniki.")
    
    # 1. Najpierw pobieramy plik, aby móc załadować kolumny
    # Wywołanie bez kolumn, aby wyrenderować górną część sidebaru
    
    # Używamy tricku: renderujemy sidebar "na raty" lub po prostu wczytujemy plik wewnątrz main,
    # a potem przekazujemy kolumny do sidebaru. Streamlit reruns script on change.
    
    # Placeholder na sidebar, który wypełnimy później lub prościej:
    # Renderujemy sidebar w całości, ale część opcji jest warunkowa.
    
    # UWAGA: W Streamlit file_uploader musi być wywołany, byśmy mieli plik. 
    # Więc najpierw wywołujemy sidebar (z pustą listą kolumn jeśli plik nie wgrany)
    
    # Aby to zrobić czysto, musimy podzielić logikę lub użyć session_state. 
    # Tutaj uprościmy: Najpierw file uploader.
    
    st.sidebar.header("📁 Dane")
    uploaded_file = st.sidebar.file_uploader("Wgraj plik CSV (maks. 10MB)", type=['csv'])
    
    # Reszta zmiennych
    user_api_key = ""
    target_col = None
    problem_type_mode = "Auto"
    
    # Sprawdzamy plik
    if uploaded_file:
        if uploaded_file.size > 10 * 1024 * 1024:
            st.sidebar.error("🚨 Plik jest za duży! Maks. 10MB.")
            uploaded_file = None
        else:
            # Wczytanie danych
            try:
                df_raw = load_data(uploaded_file)
                columns = df_raw.columns.tolist()
                
                # --- DALSZA CZĘŚĆ SIDEBARU (KONFIGURACJA) ---
                st.sidebar.divider()
                st.sidebar.header("⚙️ Konfiguracja")
                
                target_col = st.sidebar.selectbox("🎯 Kolumna Celu (Target):", columns)
                
                mode_options = {
                    "Automatyczny (Zalecane)": "Auto",
                    "Klasyfikacja (Ręczny)": "klasyfikacja",
                    "Regresja (Ręczny)": "regresja"
                }
                
                selected_mode_label = st.sidebar.radio(
                    "Tryb modelu:",
                    list(mode_options.keys()),
                    help="Wybierz 'Auto', aby system sam wykrył typ problemu."
                )
                problem_type_mode = mode_options[selected_mode_label]
            except Exception as e:
                st.error(f"Nie udało się wczytać pliku: {e}")
                df_raw = None

    # --- DALSZA CZĘŚĆ SIDEBARU (API I INFO) ---
    st.sidebar.divider()
    st.sidebar.warning(
        "Nazwy kolumn są przesyłane do OpenAI. Nie wgrywaj danych RODO."
    )
    st.sidebar.header("🔑 API Key")
    user_api_key = st.sidebar.text_input(
        "Klucz OpenAI API",
        type="password",
        value=os.getenv("OPENAI_API_KEY", "")
    )
    
    # --- GŁÓWNA CZĘŚĆ APLIKACJI ---
    
    if uploaded_file and 'df_raw' in locals() and df_raw is not None:
        try:
            # Preprocessing
            with st.spinner("🧹 Analiza wstępna danych..."):
                df, cleaning_logs = AnalysisService.preprocess_data(df_raw)
            
            # Karty metryk
            with st.container():
                st.subheader("🔍 Podgląd Danych")
                render_metrics(df)
                with st.expander("Pokaż próbkę danych i logi czyszczenia"):
                    st.dataframe(df.head(5), use_container_width=True)
                    st.text(cleaning_logs)
            
            st.divider()
            
            # Przycisk startu (teraz duży i wyraźny)
            col_spacer, col_btn, col_spacer2 = st.columns([1, 2, 1])
            with col_btn:
                start_btn = st.button("🚀 Rozpocznij Analizę", type="primary", use_container_width=True)
            
            if start_btn:
                if not target_col:
                    st.error("Proszę wybrać kolumnę celu w panelu bocznym.")
                else:
                    # Monitor Pamięci Start
                    st.markdown("### 🧬 Przebieg Procesu")
                    mem_col1, mem_col2 = st.columns([1, 2])
                    with mem_col1:
                        status_box = st.empty()
                        status_box.info("Inicjalizacja środowiska...")
                    with mem_col2:
                        chart_box = st.empty()

                    monitor = MemoryMonitor(chart_box, status_box)
                    monitor.start_background_monitoring(interval=1.0)

                    try:
                        with st.spinner("⚙️ Trenowanie modeli (Może to potrwać 1-2 minuty)..."):
                            # Decyzja o typie problemu
                            if problem_type_mode == "Auto":
                                problem_type = AnalysisService.determine_problem_type(df, target_col)
                                st.info(f"System wykrył typ problemu: **{problem_type.upper()}**")
                            else:
                                problem_type = problem_type_mode
                                st.info(f"Użyto trybu ręcznego: **{problem_type.upper()}**")
                            
                            # Uruchomienie PyCaret
                            imp_df, model_or_err = AnalysisService.run_analysis(df, target_col, problem_type)
                            
                            monitor.stop_background_monitoring()
                            
                            if imp_df is not None:
                                status_box.success("✅ Analiza zakończona sukcesem!")
                                
                                st.divider()
                                res_col1, res_col2 = st.columns([1.2, 1])
                                
                                with res_col1:
                                    st.subheader("📈 Ranking Cech")
                                    fig = px.bar(
                                        imp_df.head(15), 
                                        x='Importance', 
                                        y='Feature', 
                                        orientation='h', 
                                        color='Importance',
                                        color_continuous_scale='Viridis',
                                        title=None
                                    )
                                    fig.update_layout(
                                        yaxis={'categoryorder':'total ascending'},
                                        margin=dict(l=0, r=0, t=0, b=0)
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
                                    
                                with res_col2:
                                    st.subheader("📝 Wnioski Biznesowe")
                                    client = ConfigService.get_openai_client(user_api_key, langfuse_active)
                                    data_info = f"Wierszy: {len(df)}, Kolumny: {len(df.columns)}"
                                    
                                    with st.spinner("🤖 Generowanie opisu AI..."):
                                        desc = OpenAIService.generate_description(
                                            client, imp_df, problem_type, target_col, data_info, langfuse_active
                                        )
                                    
                                    st.markdown(desc)
                                    
                            else:
                                status_box.error("Błąd podczas treningu.")
                                st.error(f"Szczegóły błędu: {model_or_err}")

                    except Exception as e:
                        monitor.stop_background_monitoring()
                        st.error(f"Krytyczny błąd aplikacji: {str(e)}")
                    finally:
                        monitor.stop_background_monitoring()

        except Exception as e:
            st.error(f"Błąd przetwarzania pliku: {str(e)}")
    else:
        # Stan pusty (landing page state)
        st.info("👈 Rozpocznij od wgrania pliku CSV w panelu bocznym.")
        
        # Opcjonalnie: Demo data button (można dodać w przyszłości)

if __name__ == "__main__":
    main()