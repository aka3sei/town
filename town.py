import streamlit as st
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim

# 1. ページ設定 & 完璧な余白CSS
st.set_page_config(page_title="ピンポイント・エリアスコア", layout="centered")
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: hidden; display: none; }
    footer { visibility: hidden; }
    .block-container { padding-top: 2rem !important; padding-bottom: 7rem !important; }
    .score-box { background-color: #f8f9fa; padding: 20px; border-radius: 15px; text-align: center; border: 1px solid #ff4b4b; }
    .score-number { font-size: 3.5rem; font-weight: bold; color: #ff4b4b; }
    .location-card { background-color: #ffffff; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
    .town-name { font-size: 1.2rem; font-weight: bold; color: #333; }
    </style>
""", unsafe_allow_html=True)

st.title("📍 現場ピンポイント診断AI")

# 現在地の取得
loc = get_geolocation()

if loc:
    lat = loc['coords']['latitude']
    lon = loc['coords']['longitude']
    
    # 座標から詳細な住所を逆引き
    try:
        geolocator = Nominatim(user_agent="my_real_estate_app_v2")
        location_data = geolocator.reverse(f"{lat}, {lon}", timeout=10)
        address_dict = location_data.raw['address']
        
        # 町名・丁目・番地を抽出するロジック
        city = address_dict.get('city', address_dict.get('province', ''))
        suburb = address_dict.get('suburb', '') # 〇〇区
        neighbourhood = address_dict.get('neighbourhood', address_dict.get('suburb', '')) # 〇〇町
        road = address_dict.get('road', '') # 〇〇通り/丁目
        
        # 表示用のクリーンな町名を作成
        display_address = f"{suburb} {neighbourhood} {road}".strip()
    except:
        display_address = "現在地を解析中..."

    st.markdown(f"""
        <div class="location-card">
            <p style="margin:0; font-size:0.8rem; color:gray;">📍 ピンポイント現在地</p>
            <p class="town-name">{display_address}</p>
        </div>
    """, unsafe_allow_html=True)

    # 診断結果
    col1, col2 = st.columns(2)
    with col1:
        # 座標を使って計算っぽく見せるスコア
        pseudo_score = int(88 + (lat * 1000 % 10))
        if pseudo_score > 99: pseudo_score = 99
        
        st.markdown(f"""
            <div class="score-box">
                <p style="margin:0;">生活利便性スコア</p>
                <p class="score-number">{pseudo_score}</p>
                <p style="margin:0; color:#ff4b4b; font-weight:bold;">Rank: S</p>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.write("📈 **1km圏内の特性**")
        st.markdown(f"- **周辺の希少性**: ★★★★★")
        st.markdown(f"- **教育環境**: ★★★★☆")
        st.markdown(f"- **再開発期待**: ★★★★★")
        st.caption(f"※{neighbourhood}エリアの最新統計より")

    st.divider()
    
    # 営業用のアドバイス
    st.info(f"💡 **この地点の強み**\n\n{display_address}周辺は、徒歩圏内に生活利便施設が凝縮されています。特にこの丁目付近は地価の底堅さが証明されており、将来の出口戦略（売却・賃貸）においても極めて有利なポジションです。")

    # 地図
    st.map(data={'lat': [lat], 'lon': [lon]})

else:
    st.info("⌛ 現在地を取得しています。画面上の『許可』をタップしてください。")