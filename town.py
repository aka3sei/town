import streamlit as st
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
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

# 2. 実データ取得関数 (Overpass API)
def get_nearby_facilities(lat, lon):
    # 半径1000m以内の 学校(school), 病院(hospital), スーパー(supermarket) を取得
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json];
    (
      node["amenity"="school"](around:1000,{lat},{lon});
      node["amenity"="hospital"](around:1000,{lat},{lon});
      node["shop"="supermarket"](around:1000,{lat},{lon});
    );
    out body;
    """
    response = requests.get(overpass_url, params={'data': overpass_query})
    data = response.json()
    
    facilities = []
    for element in data['elements']:
        name = element.get('tags', {}).get('name', '名称不明')
        # 種別の日本語変換
        amenity = element.get('tags', {}).get('amenity')
        shop = element.get('tags', {}).get('shop')
        
        category = "学校" if amenity == "school" else "病院" if amenity == "hospital" else "スーパー"
        facilities.append({"施設名": name, "種別": category})
    
    return pd.DataFrame(facilities).drop_duplicates(subset="施設名")

st.title("🏙️ 暮らしの立地スコア")

loc = get_geolocation()

if loc:
    lat = loc['coords']['latitude']
    lon = loc['coords']['longitude']
    
    # 住所取得
    geolocator = Nominatim(user_agent="lifestyle_real_data")
    location_data = geolocator.reverse(f"{lat}, {lon}", timeout=10)
    st.markdown(f"📍 **現在地：{location_data.address.split(',')[0]} 付近**")

    # --- 実データの取得と表示 ---
    with st.spinner('近隣の実在施設をスキャン中...'):
        df_facilities = get_nearby_facilities(lat, lon)

    col1, col2 = st.columns([1, 1])
    with col1:
        # 施設数に応じてスコアを変動させる
        count = len(df_facilities)
        score = min(70 + (count * 2), 99)
        st.markdown(f"""
            <div class="score-box">
                <p style="margin:0; font-size:0.9rem;">実データ解析スコア</p>
                <p class="score-number">{score}</p>
                <p style="margin:0; font-weight:bold; color:#1a365d;">評価：{"S" if score > 90 else "A"}ランク</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.write("📈 **1km圏内の実数**")
        st.write(f"- 学校: {len(df_facilities[df_facilities['種別']=='学校'])} 件")
        st.write(f"- 病院: {len(df_facilities[df_facilities['種別']=='病院'])} 件")
        st.write(f"- スーパー: {len(df_facilities[df_facilities['種別']=='スーパー'])} 件")

    st.divider()

    # --- 実施設リスト ---
    if not df_facilities.empty:
        st.subheader("🔍 周辺の実在施設リスト")
        st.dataframe(df_facilities, use_container_width=True, hide_index=True)
    else:
        st.warning("1km圏内に該当施設が見つかりませんでした。")

    st.map(data={'lat': [lat], 'lon': [lon]})

else:
    st.info("⌛ 現在地を解析中です。iPhoneの『許可』をタップしてください。")
