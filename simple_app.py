import streamlit as st
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import plotly.express as px
import plotly.graph_objects as go
import warnings
warnings.filterwarnings('ignore')

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
    """Analizuje ważność cech używając Random Forest"""
    
    # Przygotowanie danych
    feature_columns = [col for col in data.columns if col != target_column]
    
    # Usuń kolumny z dużą liczbą wartości brakujących
    data_clean = data.dropna(thresh=len(data) * 0.7, axis=1)
    
    # Usuń wiersze z wartościami brakującymi
    data_clean = data_clean.dropna()
    
    if len(data_clean) < 10:
        return None, "Za mało danych po czyszczeniu"
    
    try:
        # Przygotuj dane X i y
        X = data_clean[feature_columns]
        y = data_clean[target_column]
        
        # Kodowanie kategorycznych zmiennych
        for col in X.columns:
            if X[col].dtype == 'object':
                le = LabelEncoder()
                X[col] = le.fit_transform(X[col].astype(str))
        
        # Kodowanie zmiennej docelowej dla klasyfikacji
        if problem_type == "klasyfikacja" and y.dtype == 'object':
            le_target = LabelEncoder()
            y = le_target.fit_transform(y.astype(str))
        
        # Konwersja na liczby
        X = X.astype(float)
        y = pd.to_numeric(y, errors='coerce')
        
        # Usuń wiersze z NaN po konwersji
        mask = ~(X.isna().any(axis=1) | y.isna())
        X = X[mask]
        y = y[mask]
        
        if len(X) < 5:
            return None, "Za mało danych po konwersji"
        
        # Wybierz model
        if problem_type == "klasyfikacja":
            model = RandomForestClassifier(n_estimators=100, random_state=42)
        else:
            model = RandomForestRegressor(n_estimators=100, random_state=42)
        
        # Trenuj model
        model.fit(X, y)
        
        # Pobierz ważność cech
        importance_df = pd.DataFrame({
            'Feature': feature_columns,
            'Importance': model.feature_importances_
        })
        
        # Sortuj według ważności
        importance_df = importance_df.sort_values('Importance', ascending=False)
        
        return importance_df, model
        
    except Exception as e:
        return None, f"Błąd podczas analizy: {str(e)}"

# Funkcja do generowania opisu
def generate_description(importance_df, problem_type, target_column, data_info):
    """Generuje opis słowny wyników"""
    
    if importance_df is None or len(importance_df) == 0:
        return "Nie udało się wygenerować opisu z powodu błędów w analizie."
    
    # Oblicz procenty
    total_importance = importance_df['Importance'].sum()
    importance_df['Percentage'] = (importance_df['Importance'] / total_importance) * 100
    
    top_feature = importance_df.iloc[0]
    
    description = f"""
## 📈 Analiza ważności cech

**Typ problemu:** {problem_type.title()}  
**Kolumna docelowa:** {target_column}  
**Liczba analizowanych cech:** {len(importance_df)}

### 🏆 Najważniejsze cechy:

"""
    
    for i, (_, row) in enumerate(importance_df.head(5).iterrows()):
        description += f"{i+1}. **{row['Feature']}** - {row['Percentage']:.1f}%\n"
    
    description += f"""

### 💡 Wnioski:

- **Najważniejsza cecha:** {top_feature['Feature']} ma największy wpływ ({top_feature['Percentage']:.1f}%) na {target_column}
- **Top 3 cechy** odpowiadają za {importance_df.head(3)['Percentage'].sum():.1f}% całkowitej ważności
- **Top 5 cech** odpowiadają za {importance_df.head(5)['Percentage'].sum():.1f}% całkowitej ważności

### 🎯 Rekomendacje:

1. **Skoncentruj się na** {top_feature['Feature']} - ma największy wpływ na wynik
2. **Monitoruj** top 3 cechy dla najlepszych rezultatów
3. **Rozważ uproszczenie** modelu skupiając się na najważniejszych cechach

{data_info}
"""
    
    return description

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
                        
                        # Oblicz procenty
                        total_importance = importance_df['Importance'].sum()
                        importance_df['Percentage'] = (importance_df['Importance'] / total_importance) * 100
                        
                        # Wykres ważności cech
                        fig = px.bar(
                            importance_df.head(10),
                            x='Percentage',
                            y='Feature',
                            orientation='h',
                            title="Top 10 najważniejszych cech",
                            color='Percentage',
                            color_continuous_scale='viridis'
                        )
                        fig.update_layout(height=500)
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Tabela z wynikami
                        st.subheader("📋 Szczegółowe wyniki")
                        display_df = importance_df.copy()
                        display_df['Percentage'] = display_df['Percentage'].round(2)
                        st.dataframe(display_df, use_container_width=True)
                        
                        # Generowanie opisu
                        st.header("📝 Opis wyników")
                        
                        # Przygotuj informacje o danych
                        data_info = f"Zbiór zawiera {len(data)} wierszy i {len(data.columns)} kolumn. Typ problemu: {problem_type}."
                        
                        description = generate_description(importance_df, problem_type, target_column, data_info)
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
           - Zbuduje model Random Forest
           - Wyświetli najważniejsze cechy
           - Wygeneruje opis wyników
        
        ## 📋 Wymagania dla danych:
        - Format CSV
        - Co najmniej 10 wierszy danych
        - Kolumny numeryczne lub kategoryczne
        - Maksymalnie 70% wartości brakujących w kolumnach
        
        ## ✨ Funkcje aplikacji:
        - Automatyczne rozpoznawanie typu problemu
        - Analiza ważności cech używając Random Forest
        - Interaktywne wykresy i tabele
        - Szczegółowy opis wyników z rekomendacjami
        """)

if __name__ == "__main__":
    main()
