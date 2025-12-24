import streamlit as st
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import requests
import pandas as pd

# 1. ページ設定（表示幅を少し広めに設定）
st.set_page_config(page_title="暮らしの立地スコア", layout="centered")
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: hidden; display: none; }
    footer { visibility: hidden; }
    .block-container { padding-top: 2rem !important; padding-bottom: 5rem !important; }
    .score-box { background-color: #f0f4f8; padding: 20px; border-radius: 20px; text-align: center; border: 2px solid #1a365d; }
    .score-number { font-size: 3.5rem; font-weight: bold; color: #1a365d; }
    /* テーブルのフォントサイズ調整 */
    div[data-testid="stDataFrame"] { font-size: 0.9rem; }
    </style>
""", unsafe_allow_html=True)

# 2. 実データ取得（制限なしで全件取得）
def get_nearby_facilities_with_dist(lat, lon):
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    # 検索対象：学校・病院・クリニック・スーパー・コンビニ・ドラッグストア
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
    except Exception as e:
        st.warning("⚠️ 地図データ取得中... サーバーの応答を待っています。")
        return pd.DataFrame()
    
    current_pos = (lat, lon)
    facilities = []
    
    if data and 'elements' in data:
        for element in data['elements']:
            tags = element.get('tags', {})
            name = tags.get('name', tags.get('brand', '名称不明の施設'))
            
            f_lat = element.get('lat') or element.get('center', {}).get('lat')
            f_lon = element.get('lon') or element.get('center', {}).get('lon')
            
            if not f_lat or not f_lon:
                continue
                
            dist_m = geodesic(current_pos, (f_lat, f_lon)).meters
            
            # 1.2km圏内
            if dist_m > 1200:
                continue

            walk_min = int(dist_m / 80) + 1
            
            amenity = tags.get('amenity', '')
            shop = tags.get('shop', '')
            
            if amenity in ['school', 'college', 'university', 'kindergarten']:
                category = "🏫 学校"
            elif amenity in ['hospital', 'clinic', 'doctors']:
                category = "🏥 病院・クリニック"
            elif shop in ['supermarket', 'convenience', 'drugstore']:
                category = "🛒 スーパー・買物"
            else:
                category = "📍 その他施設"
            
            facilities.append({
                "施設名": name,
                "種別": category,
                "距離": f"約{int(dist_m)}m",
                "徒歩": f"約{walk_min}分",
                "dist_raw": dist_m
            })
    
    if not facilities:
        return pd.DataFrame()

    # 距離順にソートし、重複をカット（全件返す）
    df = pd.DataFrame(facilities).sort_values("dist_raw").drop_duplicates(subset="施設名")
    return df.drop(columns=["dist_raw"])

# 3. メイン画面
st.title("🏙️ 暮らしの立地スコア")

loc = get_geolocation()

if loc:
    lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
    
    try:
        geolocator = Nominatim(user_agent="lifestyle_real_data_v7")
        location_data = geolocator.reverse(f"{lat}, {lon}", timeout=10)
        st.markdown(f"📍 **現在地付近を解析中**")
    except:
        st.markdown(f"📍 **現在地を特定しました**")

    with st.spinner('近隣の全施設データを抽出中...'):
        df_facilities = get_nearby_facilities_with_dist(lat, lon)

    # スコア計算（見つかった施設数に基づき算出）
    count = len(df_facilities)
    score = min(60 + (count * 1.2), 99)
    
    st.markdown(f"""
        <div class="score-box">
            <p style="margin:0; font-size:0.9rem;">実測データ解析スコア</p>
            <p class="score-number">{int(score)}</p>
            <p style="margin:0; font-weight:bold; color:#1a365d;">周辺施設数: {count}件</p>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    if not df_facilities.empty:
        st.subheader(f"🔍 1.2km圏内の施設一覧")
        # heightを指定して、リストが長くてもスクロールで見れるようにする
        st.dataframe(df_facilities, use_container_width=True, hide_index=True, height=600)
    else:
        st.warning("周辺に該当施設が見つかりませんでした。")

    st.map(data={'lat': [lat], 'lon': [lon]})

else:
    st.info("⌛ 現在地を取得中です。iPhoneの画面で『許可』をタップしてください。")
