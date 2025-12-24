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
    
    /* リストのデザイン調整 */
    .custom-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
    .custom-table th { background-color: #1a365d; color: white; padding: 10px; text-align: left; }
    .custom-table td { border-bottom: 1px solid #ddd; padding: 10px; }
    </style>
""", unsafe_allow_html=True)

# 2. 実データ取得
def get_nearby_facilities_with_dist(lat, lon):
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    # 公園(park)、郵便局(post_office)、銀行(bank)を含むクエリ
    overpass_query = f"""
    [out:json][timeout:30];
    (
      node["amenity"~"school|college|university|kindergarten|hospital|clinic|doctors|post_office|bank"](around:1200,{lat},{lon});
      way["amenity"~"school|college|university|kindergarten|hospital|clinic|doctors|post_office|bank"](around:1200,{lat},{lon});
      node["shop"~"supermarket|convenience|drugstore"](around:1200,{lat},{lon});
      way["shop"~"supermarket|convenience|drugstore"](around:1200,{lat},{lon});
      node["leisure"="park"](around:1200,{lat},{lon});
      way["leisure"="park"](around:1200,{lat},{lon});
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
            name = tags.get('name') or tags.get('brand')
            
            if not name or any(x in name for x in ['名称不明', '近隣施設', '不明な施設']):
                continue
            
            f_lat = element.get('lat') or element.get('center', {}).get('lat')
            f_lon = element.get('lon') or element.get('center', {}).get('lon')
            if not f_lat or not f_lon: continue
                
            dist_m = geodesic(current_pos, (f_lat, f_lon)).meters
            if dist_m > 1200: continue
            walk_min = int(dist_m / 80) + 1
            
            amenity = tags.get('amenity', '')
            shop = tags.get('shop', '')
            leisure = tags.get('leisure', '')
            
            if amenity in ['school', 'college', 'university', 'kindergarten']:
                category, cat_id = "🏫 学校", "school"
            elif amenity in ['hospital', 'clinic', 'doctors']:
                category, cat_id = "🏥 病院・クリニック", "hospital"
            elif shop in ['supermarket', 'convenience', 'drugstore']:
                category, cat_id = "🛒 スーパー・買物", "shop"
            elif amenity in ['post_office', 'bank'] or leisure == 'park':
                category, cat_id = "🌳 公園・公共・銀行", "public"
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
    
    if not facilities: 
        return pd.DataFrame(columns=["施設名", "種別", "距離", "徒歩", "dist_raw", "cat_id"])
    
    df = pd.DataFrame(facilities).sort_values("dist_raw").drop_duplicates(subset="施設名")
    return df

# 3. メイン画面
st.title("🏙️ 暮らしの立地スコア")

loc = get_geolocation()

if loc:
    lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
    
    with st.spinner('周辺施設を検索中...'):
        df_facilities = get_nearby_facilities_with_dist(lat, lon)

    # 【修正】公園・公共施設のカウント(n_public)を追加
    if not df_facilities.empty:
        n_school = len(df_facilities[df_facilities['cat_id'] == 'school'])
        n_hospital = len(df_facilities[df_facilities['cat_id'] == 'hospital'])
        n_shop = len(df_facilities[df_facilities['cat_id'] == 'shop'])
        n_public = len(df_facilities[df_facilities['cat_id'] == 'public'])
        total_count = len(df_facilities)
        # 件数が増えるのでスコア計算を調整（1件1点程度）
        score = min(55 + (total_count * 1.0), 99)
    else:
        n_school = n_hospital = n_shop = n_public = total_count = 0
        score = 50

    # 【修正】スコア詳細に公園・公共を表示
    st.markdown(f"""
        <div class="score-box">
            <p style="margin:0; font-size:0.9rem;">実測データ解析スコア</p>
            <p class="score-number">{int(score)}</p>
            <p class="score-details">
                🏫学:{n_school} / 🏥病:{n_hospital} / 🛒商:{n_shop} / 🌳公:{n_public}
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    if total_count > 0:
        st.subheader(f"🔍 周辺施設一覧 ({total_count}件)")
        
        display_df = df_facilities.drop(columns=["dist_raw", "cat_id"])
        
        html_table = display_df.to_html(index=False, classes='custom-table', escape=False)
        st.markdown(html_table, unsafe_allow_html=True)
    else:
        st.warning("周辺1.2km以内に該当施設が見つかりませんでした。")

    st.map(data={'lat': [lat], 'lon': [lon]})

else:
    st.info("⌛ 現在地を取得中です。iPhoneの画面で『許可』をタップしてください。")
