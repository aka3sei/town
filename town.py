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
    .block-container { padding-top: 2rem !important; padding-bottom: 7rem !important; }
    .score-box { background-color: #f0f4f8; padding: 20px; border-radius: 20px; text-align: center; border: 2px solid #1a365d; }
    .score-number { font-size: 3.5rem; font-weight: bold; color: #1a365d; }
    </style>
""", unsafe_allow_html=True)

# 2. 実データ取得（点データだけでなく面データの中央値も取得するように改良）
def get_nearby_facilities_with_dist(lat, lon):
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    # [out:json]の後に、中心点(center)を出すように指定
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
            name = tags.get('name', tags.get('brand', '近隣施設'))
            
            # nodeの場合はlat/lon、wayの場合はcenterのlat/lonを使用
            f_lat = element.get('lat') or element.get('center', {}).get('lat')
            f_lon = element.get('lon') or element.get('center', {}).get('lon')
            
            if not f_lat or not f_lon:
                continue
                
            dist_m = geodesic(current_pos, (f_lat, f_lon)).meters
            
            # 表示上は1.2kmまで許容（確実に件数を出すため）
            if dist_m > 1200:
                continue

            walk_min = int(dist_m / 80) + 1
            
            amenity = tags.get('amenity', '')
            shop = tags.get('shop', '')
            
            if amenity in ['school', 'college', 'university', 'kindergarten']:
                category = "🏫 学校"
            elif amenity in ['hospital', 'clinic', 'doctors']:
                category = "🏥 病院"
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

    # 距離順にソートし、重複をカットして上位20件程度表示
    df = pd.DataFrame(facilities).sort_values("dist_raw").drop_duplicates(subset="施設名")
    return df.head(20).drop(columns=["dist_raw"])

# 3. メイン画面
st.title("🏙️ 暮らしの立地スコア")

loc = get_geolocation()

if loc:
    lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
    
    try:
        geolocator = Nominatim(user_agent="lifestyle_real_data_v5")
        location_data = geolocator.reverse(f"{lat}, {lon}", timeout=10)
        st.markdown(f"📍 **現在地：{location_data.address.split(',')[0]} 付近**")
    except:
        st.markdown(f"📍 **現在地を特定しました**")

    with st.spinner('近隣施設の実データを検索中...'):
        df_facilities = get_nearby_facilities_with_dist(lat, lon)

    score = min(70 + (len(df_facilities) * 1.5), 99)
    st.markdown(f"""
        <div class="score-box">
            <p style="margin:0; font-size:0.9rem;">実測データ解析スコア</p>
            <p class="score-number">{int(score)}</p>
            <p style="margin:0; font-weight:bold; color:#1a365d;">評価：{"S" if score > 85 else "A"}ランク</p>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    if not df_facilities.empty:
        st.subheader(f"🔍 周辺の主要施設 (約20件表示)")
        st.dataframe(df_facilities, use_container_width=True, hide_index=True)
    else:
        st.warning("周辺に該当施設が見つかりませんでした。")

    st.map(data={'lat': [lat], 'lon': [lon]})

else:
    st.info("⌛ 現在地を取得中です。iPhoneのブラウザで位置情報の共有を許可してください。")
