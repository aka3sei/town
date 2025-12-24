import streamlit as st
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import requests
import pandas as pd

# 1. ページ設定
st.set_page_config(page_title="暮らしの立地スコア", layout="centered")
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: hidden; display: none; }
    footer { visibility: hidden; }
    .block-container { padding-top: 2rem !important; padding-bottom: 5rem !important; }
    .score-box { background-color: #f0f4f8; padding: 20px; border-radius: 20px; text-align: center; border: 2px solid #1a365d; }
    .score-number { font-size: 3.5rem; font-weight: bold; color: #1a365d; line-height: 1; margin-bottom: 10px; }
    .score-details { font-size: 0.9rem; color: #2c5282; font-weight: bold; }
    /* テーブルのスクロールを無効化して全件表示 */
    div[data-testid="stDataFrame"] > div { height: auto !important; }
    </style>
""", unsafe_allow_html=True)

# 2. 実データ取得
def get_nearby_facilities_with_dist(lat, lon):
    overpass_url = "https://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json][timeout:30];
    (
      node["amenity"~"school|college|university|kindergarten|hospital|clinic|doctors"](around:1200,{lat},{lon});
      way["amenity"~"school|college|university|kindergarten|hospital|clinic|doctors"](around:1200,{lat},{lon});
      node["shop"~"supermarket|convenience|drugstore"](around:1200,{lat},{lon});
      way["shop"~"supermarket|convenience|drugstore"](around:1200,{lat},{lon});
    );
    out center;
    """
    
    try:
        response = requests.get(overpass_url, params={'data': overpass_query}, timeout=15)
        response.raise_for_status() 
        data = response.json()
    except:
        return pd.DataFrame()
    
    current_pos = (lat, lon)
    facilities = []
    
    if data and 'elements' in data:
        for element in data['elements']:
            tags = element.get('tags', {})
            
            # 【修正】名称がないものはスキップ
            name = tags.get('name') or tags.get('brand')
            if not name or name in ['名称不明', '近隣施設', '不明な施設']:
                continue
            
            f_lat = element.get('lat') or element.get('center', {}).get('lat')
            f_lon = element.get('lon') or element.get('center', {}).get('lon')
            if not f_lat or not f_lon: continue
                
            dist_m = geodesic(current_pos, (f_lat, f_lon)).meters
            if dist_m > 1200: continue
            walk_min = int(dist_m / 80) + 1
            
            amenity = tags.get('amenity', '')
            shop = tags.get('shop', '')
            
            if amenity in ['school', 'college', 'university', 'kindergarten']:
                category = "🏫 学校"
                cat_id = "school"
            elif amenity in ['hospital', 'clinic', 'doctors']:
                category = "🏥 病院・クリニック"
                cat_id = "hospital"
            elif shop in ['supermarket', 'convenience', 'drugstore']:
                category = "🛒 スーパー・買物"
                cat_id = "shop"
            else:
                continue
            
            facilities.append({
                "施設名": name,
                "種別": category,
                "距離": f"約{int(dist_m)}m",
                "徒歩": f"約{walk_min}分",
                "dist_raw": dist_m,
                "cat_id": cat_id
            })
    
    if not facilities: return pd.DataFrame()
    df = pd.DataFrame(facilities).sort_values("dist_raw").drop_duplicates(subset="施設名")
    return df

# 3. メイン画面
st.title("🏙️ 暮らしの立地スコア")

loc = get_geolocation()

if loc:
    lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
    
    with st.spinner('全施設データを抽出中...'):
        df_facilities = get_nearby_facilities_with_dist(lat, lon)

    # 件数の集計
    n_school = len(df_facilities[df_facilities['cat_id'] == 'school'])
    n_hospital = len(df_facilities[df_facilities['cat_id'] == 'hospital'])
    n_shop = len(df_facilities[df_facilities['cat_id'] == 'shop'])
    total_count = len(df_facilities)

    # スコア計算
    score = min(60 + (total_count * 1.2), 99)
    
    # 【修正】内訳を表示するスコアボックス
    st.markdown(f"""
        <div class="score-box">
            <p style="margin:0; font-size:0.9rem;">実測データ解析スコア</p>
            <p class="score-number">{int(score)}</p>
            <p class="score-details">
                🏫学校:{n_school} / 🏥病院:{n_hospital} / 🛒買物:{n_shop}
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    if not df_facilities.empty:
        st.subheader(f"🔍 周辺施設一覧 ({total_count}件)")
        # 【修正】heightを指定せず、全件表示
        display_df = df_facilities.drop(columns=["dist_raw", "cat_id"])
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.warning("周辺に該当施設が見つかりませんでした。")

    st.map(data={'lat': [lat], 'lon': [lon]})

else:
    st.info("⌛ 現在地を取得中です。iPhoneの画面で『許可』をタップしてください。")
