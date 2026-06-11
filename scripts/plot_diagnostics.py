import pandas as pd
import matplotlib.pyplot as plt
import os

# --- קונפיגורציה בסיסית ---
OUTPUT_DIR = '../build/output'
R_PLANET = 50.0
H_ATMOSPHERE = 20.0

def plot_dashboard():
    # הגדרת עיצוב נקי ומקצועי (סגנון מובנה ב-Matplotlib)
    plt.style.use('ggplot')
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle('Stage 1 Diagnostics Dashboard', fontsize=18, fontweight='bold')

    # --- פאנל 1: פרופיל צפיפות רדיאלי ---
    density_file = os.path.join(OUTPUT_DIR, 'radial_density_profile.csv')
    if os.path.exists(density_file):
        df_density = pd.read_csv(density_file)
        
        ax1.plot(df_density['r_center'], df_density['number_density'], 
                 marker='o', markersize=6, linestyle='-', color='#1f77b4', linewidth=2)
        
        # הדגשת שטח מתחת לגרף למראה מקצועי
        ax1.fill_between(df_density['r_center'], df_density['number_density'], alpha=0.2, color='#1f77b4')
        
        # ציור קווי גבול של הפלנטה והאטמוספירה
        ax1.axvline(x=R_PLANET, color='black', linestyle='--', linewidth=1.5, label='Planet Surface (R)')
        ax1.axvline(x=R_PLANET + H_ATMOSPHERE, color='gray', linestyle='--', linewidth=1.5, label='Atmosphere Top (R+H)')
        
        ax1.set_title('Radial Density Profile $n(r)$', fontsize=14)
        ax1.set_xlabel('Radius (Distance from center)', fontsize=12)
        ax1.set_ylabel('Number Density', fontsize=12)
        ax1.legend(loc='upper right')
        ax1.grid(True, linestyle=':', alpha=0.7)
    else:
        ax1.text(0.5, 0.5, 'radial_density_profile.csv\nNot Found', 
                 horizontalalignment='center', verticalalignment='center', fontsize=14, color='red')

    # --- פאנל 2: שימור אנרגיה ---
    log_file = os.path.join(OUTPUT_DIR, 'simulation_log.csv')
    if os.path.exists(log_file):
        df_log = pd.read_csv(log_file)
        
        ax2.plot(df_log['step'], df_log['e_kin'], label='Kinetic', color='#ff7f0e', linewidth=2)
        ax2.plot(df_log['step'], df_log['e_grav'], label='Gravitational', color='#2ca02c', linewidth=2)
        ax2.plot(df_log['step'], df_log['e_rep'], label='Repulsion', color='#d62728', linewidth=2)
        ax2.plot(df_log['step'], df_log['e_total'], label='Total Energy', color='black', linestyle='-', linewidth=2.5)
        
        ax2.set_title('System Energy Components Over Time', fontsize=14)
        ax2.set_xlabel('Simulation Step', fontsize=12)
        ax2.set_ylabel('Energy (Model Units)', fontsize=12)
        ax2.legend(loc='center right', bbox_to_anchor=(1.0, 0.5))
        ax2.grid(True, linestyle=':', alpha=0.7)
    else:
        ax2.text(0.5, 0.5, 'simulation_log.csv\nNot Found', 
                 horizontalalignment='center', verticalalignment='center', fontsize=14, color='red')

    plt.tight_layout()
    plt.subplots_adjust(top=0.9) # פינוי מקום לכותרת הראשית
    plt.show()

if __name__ == "__main__":
    print("Loading Stage 1 Diagnostics...")
    plot_dashboard()