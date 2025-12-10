import time
import os
import psutil  # Wymaga dodania 'psutil' do requirements.txt
import logging
import streamlit as st
import gc

# Konfiguracja logowania widoczna w konsoli DigitalOcean
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_memory_usage():
    """Zwraca zużycie pamięci w MB oraz procent zużycia całego systemu."""
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    rss_mb = mem_info.rss / 1024 / 1024
    sys_mem = psutil.virtual_memory()
    return rss_mb, sys_mem.percent

def mock_training_with_streamlit():
    st.write("### 🚀 Rozpoczynam symulację treningu...")
    
    # Placeholdery w UI na wykresy i statystyki
    status_text = st.empty()
    metric_col1, metric_col2 = st.columns(2)
    progress_bar = st.progress(0)
    
    # Kontener na dane do wykresu (zbieramy historię zużycia RAM)
    memory_history = []
    chart_placeholder = st.empty()

    # Symulacja wycieku pamięci (lista, która rośnie)
    data_cache = [] 
    
    try:
        total_epochs = 5
        steps_per_epoch = 50
        
        for epoch in range(1, total_epochs + 1):
            logging.info(f"--- Rozpoczęcie epoki {epoch} ---")
            
            for batch in range(1, steps_per_epoch + 1):
                # 1. Symulacja obliczeń
                time.sleep(0.05) 
                
                # 2. Symulacja WYCIEKU PAMIĘCI (Celowe zapchanie RAM)
                # Dodajemy 5MB danych co iterację
                large_data_chunk = "x" * 1024 * 1024 * 5 
                data_cache.append(large_data_chunk) 
                
                # 3. Aktualizacja UI co 5 kroków (żeby nie spowalniać pętli)
                if batch % 5 == 0:
                    rss_mb, sys_percent = get_memory_usage()
                    memory_history.append(rss_mb)
                    
                    # Logowanie do konsoli DigitalOcean (ważne, jeśli appka padnie)
                    logging.info(f"Epoka {epoch}, Batch {batch} | RAM Procesu: {rss_mb:.2f} MB | System: {sys_percent}%")
                    
                    # Aktualizacja metryk w Streamlit
                    status_text.text(f"Epoka: {epoch}/{total_epochs} | Batch: {batch}")
                    metric_col1.metric("Zużycie RAM procesu", f"{rss_mb:.2f} MB")
                    metric_col2.metric("Zajętość RAM systemu", f"{sys_percent}%")
                    
                    # Rysowanie prostego wykresu liniowego
                    chart_placeholder.line_chart(memory_history)
                    
                    # Aktualizacja paska postępu
                    current_progress = ((epoch - 1) * steps_per_epoch + batch) / (total_epochs * steps_per_epoch)
                    progress_bar.progress(min(current_progress, 1.0))
                    
                    # Zabezpieczenie (Stop przed crashem całego serwera)
                    # DigitalOcean Basic Droplet/App ma często tylko 512MB lub 1GB RAM!
                    if sys_percent > 90:
                        st.error("⚠️ KRITICAL WARNING: Zużycie RAM > 90%! Przerywam, aby uniknąć restartu kontenera.")
                        logging.warning("Przerwano ze względu na brak pamięci.")
                        return

        st.success("Symulacja zakończona sukcesem!")

    except Exception as e:
        st.error(f"Wystąpił błąd: {e}")
        logging.error(f"Error: {e}")
    finally:
        # Sprzątanie po teście
        del data_cache
        gc.collect()
        st.info("Wyczyszczono pamięć po teście.")

# --- Interfejs Streamlit ---
st.title("🔍 Diagnostyka Pamięci na DigitalOcean")
st.write("""
To narzędzie symuluje obciążenie pamięci (Memory Leak), aby sprawdzić, 
przy jakim poziomie RAM Twoja instancja na DigitalOcean się resetuje.
""")

col1, col2 = st.columns(2)
with col1:
    if st.button("Uruchom Test Pamięci"):
        mock_training_with_streamlit()

with col2:
    if st.button("Sprawdź tylko stan obecny"):
        rss, sys_p = get_memory_usage()
        st.metric("Obecny RAM procesu", f"{rss:.2f} MB")
        st.metric("Obecny RAM systemu", f"{sys_p}%")