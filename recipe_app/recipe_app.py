from flask import Flask, jsonify, request, render_template

import numpy as np
import pandas as pd
import dill
from scipy import spatial
from nltk import LancasterStemmer
from ingredient_parser.en import parse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn import decomposition
import requests
import re
from bs4 import BeautifulSoup

analyzer = TfidfVectorizer(stop_words='english',min_df=1).build_analyzer()

stemmer = LancasterStemmer()

def stemmed_words(doc):
    return (stemmer.stem(w) for w in analyzer(doc))

recipe_similarity_df = dill.load(open('pickles/recipe_similarity_df.p', 'r'))

#---------- MODEL AND SAMPLE DF IN MEMORY ----------------#

# Load in pickled models

model = dill.load(open('pickles/nmf_model.p', 'r'))

tfidf = dill.load(open('pickles/tfidf_transformer.p', 'r'))

#---------- URLS AND WEB PAGES -------------#

# Initialize the app
app = Flask(__name__)

# Homepage
@app.route("/")
def index():

    return render_template("index.html")

# Get an example and return it's score from the predictor model
@app.route("/recs/", methods=["POST"])
def score():

    data = request.json

# Scrape ingredients for user-specified url, and format ingredients for use in recommendation system

    url = data["urls"][0]
    response = requests.get(url)
    page = response.text
    page = BeautifulSoup(page, 'lxml')
    ingredients = [i.text for i in page.findAll("span", {"class" : "recipe-ingred_txt added"})]
    parsed_input = [{'link':url.split('?internal')[0].split('.com')[1],
                   'ingredients':' '.join([re.sub(r'\([^)]*\) ', "", parse(j)['name'].lower().split(",")[0]) 
                                   for j in ingredients])}]

# Apply TFIDF, followed by NMF transformation to specified url                   

    tfidf_transformation = tfidf.transform([parsed_input[0].values()[1]])
    flavor_transformation = model.transform(pd.DataFrame(tfidf_transformation.todense()))
    flavor_transformation = pd.DataFrame(flavor_transformation, index=[parsed_input[0]['link']], columns = ['topic_' + str(i) for i in range(1,21)])

# Find closest recipe matches, and also return flavor alignments

    match_dict = []
    for i in recipe_similarity_df.iterrows():
        if i[0] != parsed_input[0]['link']:
            match_dict.append({'link':i[0],'sim_score':1-spatial.distance.cosine(flavor_transformation,i[1])})

    match_results = sorted(match_dict, key = lambda x: x['sim_score'], reverse=True)[:3]

    flavor_dict = [{parsed_input[0]['link']: dict(flavor_transformation.ix[0,:])}]
    for i in match_results:
        flavor_dict.append({i['link']:dict(recipe_similarity_df.ix[i['link'],:])})

    flavor_list = []
    recipes = []
    for i in flavor_dict:
        flavor_list.extend(i.values())
        recipes.append(i.keys()[0])

    flavor_frame = pd.DataFrame(flavor_list, index=recipes)    
    flavor_frame = flavor_frame[sorted(flavor_frame.columns, key = lambda x: int(x.split('_')[-1]))].T
    flavor_frame.index = ['Basic Seasonings', 'Baking', 'Milk and Cream', 'Asian Inspired', 'Earthy Veggies', 'Seafood', 'Breads',
                          'Beans and Chili', 'Pork', 'Citrus', 'Cheese', 'Dry Spices', 'Pastries', 'Stews', 'Fresh Veggies',
                          'Fillings', 'Sweet and Rich', 'Herbs', 'Soups and Stocks', 'Garnishes']
    flavor_frame.to_csv('static/flavor_df.csv',index_label='topic')
    
    bar_chart_data = []

    for i in flavor_frame.iterrows():
        data_dict = {}
        score_list = []
        for j in i[-1].iteritems():
            data_dict[j[0]] = j[1]
            score_list.append({'name':j[0], 'value':j[1]})
        data_dict['topic'] = i[0]
        data_dict['scores'] = score_list
        bar_chart_data.append(data_dict)

# Scrape allrecipes.com for pictures and descripions of these matches, for visualization in the app.  Also send flavor alignment data.        

    results = {}

    for i in range(3):
        url = 'http://allrecipes.com'+match_results[i]['link']
        response = requests.get(url)
        page = response.text
        page = BeautifulSoup(page, 'lxml')
        desc = page.find("div", {"class" : "submitter__description"}).text.strip()
        img_link = page.find("img", {"class" : "rec-photo"})['src']
        results[str(i+1)] = {'link':'http://allrecipes.com'+match_results[i]['link'], 
                             'desc': desc, 
                             'img':img_link,
                             'title':' '.join([str(j.capitalize()) for j in match_results[i]['link'].split('/')[-2].split('-')])}
        results[str(i+1)].update(flavor_dict[i+1][match_results[i]['link']])

    results['input'] = flavor_dict[0][parsed_input[0]['link']]
    results['chart_data'] = bar_chart_data
        
    print(results)          

    return jsonify(results)

#--------- RUN WEB APP SERVER ------------#

# Start the app server
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
