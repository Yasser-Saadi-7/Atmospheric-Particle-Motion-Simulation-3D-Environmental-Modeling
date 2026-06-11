import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import glob
import os

# --- הגדרות הסימולציה ---
OUTPUT_DIR = '../build/output'
R_PLANET = 50.0
H_ATMOSPHERE = 20.0

def get_latest_snapshot(output_dir):
    search_pattern = os.path.join(output_dir, 'particles_step_*.csv')
    files = glob.glob(search_pattern)
    if not files:
        return None
    return max(files, key=os.path.getctime)

def draw_wireframe_sphere(ax, radius, color, alpha, label):
    """מצייר כדור רשת תלת ממדי במרכז"""
    u, v = np.mgrid[0:2*np.pi:30j, 0:np.pi:15j]
    x = radius * np.cos(u) * np.sin(v)
    y = radius * np.sin(u) * np.sin(v)
    z = radius * np.cos(v)
    ax.plot_wireframe(x, y, z, color=color, alpha=alpha, linewidth=0.5, label=label)

def plot_particles_3d(filename):
    print(f"Loading 3D data from:\n> {filename}")
    try:
        df = pd.read_csv(filename)
    except Exception as e:
        print(f"Error loading file: {e}")
        return

    # חילוץ נתונים
    x, y, z = df['x'], df['y'], df['z']
    temperatures = df['temperature']
    step = df['step'].iloc[0]

    # --- הגדרת המראה הגרפי (Dark Mode) ---
    plt.style.use('dark_background')
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')
    ax.set_facecolor('black')

    # ביטול צבע הרקע של הצירים עצמם
    ax.xaxis.set_pane_color((0.0, 0.0, 0.0, 0.0))
    ax.yaxis.set_pane_color((0.0, 0.0, 0.0, 0.0))
    ax.zaxis.set_pane_color((0.0, 0.0, 0.0, 0.0))

    # --- ציור גיאומטריית הרקע ---
    draw_wireframe_sphere(ax, R_PLANET, color='cyan', alpha=0.3, label='Planet Surface')
    draw_wireframe_sphere(ax, R_PLANET + H_ATMOSPHERE, color='white', alpha=0.05, label='Atmosphere Limit')

    # --- ציור החלקיקים ---
    # שימוש ב-plasma, מפת צבעים שמתאימה מאוד לרקע כהה
    scatter = ax.scatter(x, y, z, c=temperatures, cmap='plasma', s=15, alpha=0.8, edgecolors='none')

    # הוספת סרגל צבעים (Colorbar) אסתטי
    cbar = plt.colorbar(scatter, ax=ax, shrink=0.6, pad=0.05)
    cbar.set_label('Internal Temperature ($T_p$)', color='white', fontsize=12)
    cbar.ax.yaxis.set_tick_params(color='white')
    plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')

    # --- הגדרת מצלמה וגבולות ---
    max_bound = R_PLANET + H_ATMOSPHERE + 5
    ax.set_xlim([-max_bound, max_bound])
    ax.set_ylim([-max_bound, max_bound])
    ax.set_zlim([-max_bound, max_bound])

    ax.set_title(f'Lagrangian Atmospheric Simulation\nStep: {step}', color='white', fontsize=16, fontweight='bold')
    
    # הסרת מספרי הצירים כדי לתת מראה נקי של "חלל" (אופציונלי)
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.set_zticklabels([])

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    target_file = get_latest_snapshot(OUTPUT_DIR)
    if target_file:
        plot_particles_3d(target_file)
    else:
        print(f"No snapshot files found in '{OUTPUT_DIR}'.")