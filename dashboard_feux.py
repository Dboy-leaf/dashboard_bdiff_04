

import streamlit as st
import geopandas as gpd
import pandas as pd 
import plotly.express as px 


st.title("Tableau de bord interactif des Feux de Forêt Alpe-de-Haute-Provence.")
st.header("Cartographie des incendies par communes.")

### Chargement des données en cache avec st.cache_data pour éviter les latences. 

@st.cache_data
def load_data(): 
   
    # Chargement de la couche communes depuis un GeoPackage. (on a vérifie en amont le nom de la couche correspondante.)
    gpk_path = 'communes_04.gpkg'
    com = gpd.read_file(gpk_path)
    com = com.to_crs("EPSG:4326") # On reprojette sur le bon CRS. 
    com['code_insee'] = com['code_insee'].astype(str) # On s'assure que le 'code_insee' soit en type str

    # Chargement du CSV BDIFF qui contient les données sur les feux. 
    df_feux = pd.read_csv("BDIFF_DB.csv", sep=';')
    df_feux['Code INSEE'] = df_feux['Code INSEE'].astype(str).str.zfill(5) # On s'assure que le 'Code INSEE' soit en type str et codé sur 5 char. 

    return com, df_feux # Ici la fonction retourne deux éléments (tuples) Un GDF Communes et un DF feux. pret a être joint. 



# Ici on assigne les deux jeux de données a deux variables différentes. 
com_global, df_feux_global = load_data()

# Filtre sur les communes pour récupérer les com du 04 uniquement. 
com_04 = com_global[com_global['code_insee_du_departement'] == '04']



### Création du slider streamlit

# On assigne deux variable pour les dates limites. 
min_year = int(df_feux_global['Année'].min())
max_year = int(df_feux_global['Année'].max())

# creation du slider avec st.slider()
select_year = st.slider(
    "Sélectionnez l'année de l'analyse :",
    min_value=min_year,
    max_value=max_year,

    value=2008, # Année par défault quand on charge le dashboard. 
    step=1  # Le pas du slider. 
)



### Filtre sur la base BDIFF et Groupby pour l'analyse. 

# On indique ici que les données feux doivent être celle de l'année choisit via le slider. 
feux_annee = df_feux_global[df_feux_global['Année'] == select_year]

# On compte les feux par commune et leurs surface pour cette année. 
feux_agreg = feux_annee.groupby('Code INSEE').agg(
    Nombre_de_feux=('Numéro', 'count'),
    surface_brulée=('surf_ha', 'sum')
).reset_index()

# On joint ces données sur le fond de carte communes du 04
map_data = com_04.merge(
    feux_agreg,
    left_on='code_insee',
    right_on='Code INSEE',
    how='left' # Garde toutes les communes même sans feux.
)

# On remplit les vides (NaN) par 0
map_data['Nombre_de_feux'] = map_data['Nombre_de_feux'].fillna(0)
map_data['surface_brulée'] = map_data['surface_brulée'].fillna(0)


# 6. Cartographie et mise en page. 
fig = px.choropleth_mapbox(
    map_data,
    geojson=map_data.geometry,
    locations=map_data.index,
    color='Nombre_de_feux',
    hover_data={'code_insee': True, 'nom_officiel': True, 'Nombre_de_feux': True, 'surface_brulée': True, }, # Info au survol (popup) 

    # Style de la carte
    mapbox_style='open-street-map',
    zoom=8,
    center={"lat": 44.0, "lon": 6.0},
    opacity=0.8,
    height=600,
    color_continuous_scale="Reds", # Échelle de rouge pour les feux
    title=f"Nombre de feux par commune en {select_year}"
)

fig.update_layout(margin={"r":0,"t":50,"l":0,"b":0}) # Parametre d'affichage définition des marges. 
st.plotly_chart(fig, width='stretch') # Affichage 



st.divider() # Ajoute une séparation (ligne)

st.title("Analyse de l'évolution des incendies sur l'ensemble du départements.")

### Graphique

# On compte le nombres de feux et la surfaces brulée par années. 
evolution = df_feux_global.groupby("Année").agg(
    Nombre = ("Année", 'count'),
    Surface = ("surf_ha", 'sum')
).reset_index()

evolution['Surface'] = evolution['Surface'].astype(int)


### Création du boutons switch streamlit.

# Demande à l'utilisateur de choisir la métrique. 
metric_choice = st.radio(
    "Sélectionnez la métrique à visualiser :", 
    ('Nombre de Feux', 'Surface Brûlée')
)

# Détermine la colonne et le titre à utiliser.
if metric_choice == 'Nombre de Feux':
    y_col = 'Nombre'
    y_title = 'Nombre de Feux'
else: # Surface Brûlée
    y_col = 'Surface'
    y_title = 'Surface brûlée (Ha)'


# 3. Création et Affichage du Graphique Unique
fig_evol = px.line(
    evolution, 
    x='Année', 
    y=y_col, # Renvoie a la condition IF ELSE
    color_discrete_sequence=['black'],
    labels={y_col: y_title},
    markers=True
)


# Configuration finale
fig_evol.update_layout(xaxis_title="Année", yaxis_title=y_title, yaxis_tickformat="d") # yaxis_tickformat="d" formate l'affichage des surfaces brulée. 

# Affichage Streamlit
st.plotly_chart(fig_evol, use_container_width=True)


st.write(evolution)

st.divider()


### Graphique interactif par choix de communes 

st.header("Analyse d'évolution des incendies par communes spécifique")

# Trie des communes dans l'ordre alphabétique
list_com = sorted(com_04['nom_officiel'].unique()) # Permet de trier la colonnes communes dans l'ordre alphabetique

# Selectbox pour le choix des communes
com_select = st.selectbox("Selectionez une commune :", list_com)

# Ici on veut récupérer les données sur la communes selectioner uniquement
feux_com = df_feux_global[df_feux_global['Commune'] == com_select]

# Groupby pour l'analyse 
evolution_com = feux_com.groupby('Année').agg(
    Nombre_par_com = ("Numéro", 'count'),
    Surface_par_com = ("surf_ha", "sum")
).reset_index() # On reset index pour conserver les noms des colonnes determiné


# Création des graphiques interactif comparaison entre surf et nombre par commune
evolution_long = pd.melt(   # .melt permet de mettre en forme deux données dans deux champs différents
    evolution_com, 
    id_vars=['Année'],
    value_vars=['Nombre_par_com', 'Surface_par_com'], # Les deux champs
    var_name='Métrique',
    value_name='Valeur'
)

# Mise en page du graphique 
fig_evol_com_final = px.line(
    evolution_long, 
    x='Année', 
    y='Valeur', 
    color='Métrique', # L'argument CLÉ pour tracer les deux lignes distinctes
    title=f"Évolution des métriques des feux à {com_select}", 
    markers=True,
    labels={
        'Métrique': 'Métrique Analysée', 
        'Valeur': 'Valeur (Nombre de Feux ou Surface Ha)'
    }
)

st.plotly_chart(fig_evol_com_final, width='stretch')

st.divider()

st.write("Tom LAURENZATI, BDIFF, IGN")
st.write("Dans le cadre d'un rendu de MASTER 2 en Géomatique et modélisation spatial a l'université d'Aix-Marseille")
