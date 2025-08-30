## Agent Recommends (reference branch)

Purpose: This branch is a read-only reference for proposed fixes and improvements. It does not affect `main` unless you merge it. Use the code snippets below in Cursor to apply edits.

### How to use
- Point Cursor to branch `agent-recommends` to view this doc.
- Paste each file's code block into Cursor to apply the changes safely.

---

### requirements.txt
Issue: Loosely pinned versions can cause env variance. Pin consistent, compatible versions.

Replace contents with:
```text
requests==2.31.0
pandas==2.2.2
numpy==1.26.4
streamlit==1.35.0
plotly==5.20.0
python-dateutil==2.9.0.post0
scikit-learn==1.4.2
matplotlib==3.8.4
seaborn==0.13.2
schedule==1.2.1
aiohttp==3.9.5
pulp==2.7.0
```

---

### fpl_api.py
Issues:
- points_per_game computed from total_points/starts can divide by zero and differs from official API field.
- Several numeric fields arrive as strings; coerce safely.

Apply inside get_players_data() after creating `df = pd.DataFrame(players_data)`:
```python
# Safe numeric coercions
df['form_float'] = pd.to_numeric(df.get('form', 0), errors='coerce').fillna(0.0)
df['now_cost'] = pd.to_numeric(df.get('now_cost', 0), errors='coerce').fillna(0).astype(int)
df['total_points'] = pd.to_numeric(df.get('total_points', 0), errors='coerce').fillna(0).astype(int)
df['minutes'] = pd.to_numeric(df.get('minutes', 0), errors='coerce').fillna(0).astype(int)
df['bonus'] = pd.to_numeric(df.get('bonus', 0), errors='coerce').fillna(0).astype(int)

# Use API-provided PPG when available; fallback to minute-normalized ratio
ppg_api = pd.to_numeric(df.get('points_per_game', None), errors='coerce')
df['points_per_game'] = ppg_api.where(ppg_api.notna(), (df['total_points'] / df['minutes'].replace(0, 1) * 90))

df['value'] = df['now_cost'] / 10.0
df['value_per_point'] = df['value'] / df['total_points'].replace(0, 1)
```

---

### analysis_engine.py
Issues:
- Normalizations divide by zero when max is 0.
- predict_player_points assumes player exists.

Add helper near top-level functions:
```python
def _safe_max(series, default=1.0):
    try:
        m = series.max()
        return m if pd.notna(m) and m > 0 else default
    except Exception:
        return default
```

Replace score normalizations in calculate_player_scores():
```python
df['form_score'] = (df['form_float'] / _safe_max(df['form_float'])) * 30
df['value_score'] = (1.0 / df['value_per_point']).replace([np.inf, -np.inf], 0)
df['value_score'] = (df['value_score'] / _safe_max(df['value_score'])) * 25
df['minutes_score'] = (df['minutes'] / _safe_max(df['minutes'])) * 20
df['recent_score'] = (df['points_per_game'] / _safe_max(df['points_per_game'])) * 15
df['bonus_score'] = (df['bonus'] / _safe_max(df['bonus'])) * 10
```

Guard in predict_player_points():
```python
player_rows = self.players_df[self.players_df['id'] == player_id]
if player_rows.empty:
    return 0.0
player = player_rows.iloc[0]
```

---

### transfer_optimizer.py
Issues:
- Uses `starts` directly; may be missing or zero.
- Minutes factor divides by current_gw*90; guard denominator.
- Coerce numeric fields safely.

Edits:
```python
# In _calculate_base_projection
current_gw = max(1, self.api.get_current_gameweek())
denom = max(current_gw * 90, 1)
minutes_played = float(player.get('minutes', 0))
minutes_factor = min(minutes_played / denom, 1.0)

bonus_total_points = max(int(player.get('total_points', 0)), 1)
bonus_points = float(player.get('bonus', 0))
bonus_factor = 1.0 + (bonus_points / bonus_total_points) * 0.1
```

```python
# In _calculate_position_adjustment
position = int(player.get('element_type', 0) or 0)
starts = int(player.get('starts', 0) or 0)
if position == 1:
    cs = float(player.get('clean_sheets', 0))
    cs_rate = cs / max(starts, 1)
    return 1.0 + cs_rate * 0.1
elif position == 2:
    attacking_bonus = (float(player.get('goals_scored', 0)) + float(player.get('assists', 0))) / 10.0
    return 1.0 + attacking_bonus * 0.1
elif position == 3:
    ict_index = pd.to_numeric(player.get('ict_index', 0), errors='coerce')
    ict_bonus = (ict_index / 100.0) if pd.notna(ict_index) else 0.0
    return 1.0 + ict_bonus * 0.05
else:
    goal_bonus = float(player.get('goals_scored', 0)) / 10.0
    return 1.0 + goal_bonus * 0.1
```

```python
# In _calculate_availability_adjustment
starts = int(player.get('starts', 0) or 0)
minutes = float(player.get('minutes', 0) or 0)
games_started = max(starts, 1)
minutes_per_game = minutes / games_started
availability_factor = min(minutes_per_game / 90.0, 1.0)
if minutes < games_started * 45:
    availability_factor *= 0.9
return max(0.7, availability_factor)
```

---

### app.py
Issue: URL extractors are brittle. Harden parsing to tolerate queries/fragments.

Replace the two functions:
```python
def extract_manager_id_from_url(team_url: str) -> Optional[int]:
    if not team_url:
        return None
    try:
        s = str(team_url).strip()
        s = s.split('?')[0].split('#')[0]
        if 'entry/' in s:
            segment = s.split('entry/', 1)[1]
            candidate = segment.split('/', 1)[0]
            return int(candidate)
    except Exception:
        return None
    return None

def extract_league_id_from_url(league_url: str) -> Optional[int]:
    if not league_url:
        return None
    try:
        s = str(league_url).strip()
        s = s.split('?')[0].split('#')[0]
        if 'leagues/' in s:
            segment = s.split('leagues/', 1)[1]
            candidate = segment.split('/', 1)[0]
            return int(candidate)
    except Exception:
        return None
    return None
```

---

### start_app.sh
Issue: Exits on test failures; make tests optional and improve dependency install.

Replace test/install logic with:
```bash
echo "🔍 Checking dependencies..."
python3 -c "import streamlit, pandas, plotly" 2>/dev/null || {
  echo "⚠️  Dependencies not found. Installing..."
  pip install -r requirements.txt || { echo "❌ Failed to install dependencies."; exit 1; }
}

# Run tests (optional)
if [ "$SKIP_TESTS" != "1" ]; then
  echo "🧪 Running quick tests..."
  if ! python3 run_tests.py; then
    echo "⚠️  Tests failed. Continuing to start the app (set SKIP_TESTS=1 to skip)."
  else
    echo "✅ All tests passed!"
  fi
fi
```

---

### run_tests.py
Issue: Entire suite depends on live FPL API; skip gracefully when offline.

Add near top:
```python
import socket

def _has_network(timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("fantasy.premierleague.com", 443))
        return True
    except Exception:
        return False
```

Then in main():
```python
network_ok = _has_network()
tests = []
if network_ok:
    tests.extend([test_api_client, test_analysis_engine, test_transfer_optimizer])
else:
    print("🌐 No network or FPL API unreachable; skipping API-dependent tests.")
tests.append(test_app_components)
```

---

### Next steps
1) Apply these edits in Cursor (on a feature branch) and run:
```bash
pip install -r requirements.txt
python run_tests.py
streamlit run app.py
```
2) If errors surface, share the output and we’ll adjust.

