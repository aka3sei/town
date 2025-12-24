import streamlit as st
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
from geopy.distance import geodesic # 距離計算用
import requests
import pandas as pd

# 1. ページ設定 & 余白CSS
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

# 2. 実データ取得と距離計算（エラー対策強化版）
def get_nearby_facilities_with_dist(lat, lon):
    # Overpass APIのエンドポイント（混雑時は日本に近いサーバーなどに変えることも可能ですが、まずは標準を強化）
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    # クエリにタイムアウトを設定し、正規表現で取得を効率化
    overpass_query = f"""
    [out:json][timeout:30];
    (
      node["amenity"~"school|hospital"](around:1000,{lat},{lon});
      node["shop"="supermarket"](around:1000,{lat},{lon});
    );
    out body;
    """
    
    try:
        # 15秒待っても応答がなければタイムアウトさせる
        response = requests.get(overpass_url, params={'data': overpass_query}, timeout=15)
        response.raise_for_status() 
        data = response.json()
    except Exception as e:
        # 通信エラーや混雑時にクラッシュさせず、ログを出して空のリストを返す
        st.warning("⚠️ 現在、地図データサーバーが混雑しています。施設リストが表示されない場合は、少し時間を置いて再読み込みしてください。")
        return pd.DataFrame()
    
    current_pos = (lat, lon)
    facilities = []
    
    # 取得データの中身をチェック
    if data and 'elements' in data:
        for element in data['elements']:
            tags = element.get('tags', {})
            name = tags.get('name', tags.get('operator', '不明な施設'))
            
            # 座標がないデータはスキップ
            if 'lat' not in element or 'lon' not in element:
                continue
                
            f_lat, f_lon = element['lat'], element['lon']
            
            # 距離計算 (メートル)
            dist_m = geodesic(current_pos, (f_lat, f_lon)).meters
            walk_min = int(dist_m / 80) + 1 # 80m=1分
            
            amenity = tags.get('amenity')
            category = "🏫 学校" if amenity == "school" else "🏥 病院" if amenity == "hospital" else "🛒 スーパー"
            
            facilities.append({
                "施設名": name,
                "種別": category,
                "距離": f"{int(dist_m)}m",
                "徒歩": f"約{walk_min}分",
                "dist_raw": dist_m
            })
    
    if not facilities:
        return pd.DataFrame()

    # 距離順にソートし、重複を排除
    df = pd.DataFrame(facilities).sort_values("dist_raw").drop_duplicates(subset="施設名").drop(columns=["dist_raw"])
    return df

st.title("🏙️ 暮らしの立地スコア")

loc = get_geolocation()

if loc:
    lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
    
    # 住所特定
    geolocator = Nominatim(user_agent="lifestyle_real_data_v4")
    location_data = geolocator.reverse(f"{lat}, {lon}", timeout=10)
    st.markdown(f"📍 **現在地：{location_data.address.split(',')[0]} 付近**")

    # データ取得
    with st.spinner('近隣施設との距離を計測中...'):
        df_facilities = get_nearby_facilities_with_dist(lat, lon)

    # --- スコア表示 ---
    score = min(75 + (len(df_facilities) * 2), 99)
    st.markdown(f"""
        <div class="score-box">
            <p style="margin:0; font-size:0.9rem;">実測データ解析スコア</p>
            <p class="score-number">{score}</p>
            <p style="margin:0; font-weight:bold; color:#1a365d;">評価：{"S" if score > 90 else "A"}ランク</p>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    # --- 施設リスト表示 ---
    if not df_facilities.empty:
        st.subheader("🔍 周辺の実在施設リスト (1km圏内)")
        st.dataframe(df_facilities, use_container_width=True, hide_index=True)
    else:
        st.warning("1km圏内に実在施設が見つかりませんでした。")

    st.map(data={'lat': [lat], 'lon': [lon]})

else:
    st.info("⌛ 現在地を解析中です。iPhoneの『許可』をタップしてください。")

