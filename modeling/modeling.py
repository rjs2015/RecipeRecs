import numpy as np
import pandas as pd
from collections import defaultdict
from collections import Counter

from nltk import LancasterStemmer
from ingredient_parser.en import parse
from scipy import spatial
import string
import re

import pickle
import dill
from pymongo import MongoClient
client = MongoClient()

from sklearn.feature_extraction.text import CountVectorizer,TfidfVectorizer
from sklearn import decomposition

# Retrieve recipes from MongoDB, clean ingredients, and fit NMF to a TFIDF of recipe ingredients,
# ultimately using the components to compute similarity between ingredients

def fetch_recipes(database_connection, client=MongoClient()):
    '''Get all recipes stored in a MongoDB allrecipe.com database collection, 
       returning a dict with the links as keys'''
    
    cursor = database_connection.find()
    recipe_database = {}

    for i in range(database_connection.count()):
        recipe = cursor.next()
        recipe_database[recipe['link']] = recipe
    
    return recipe_database

def get_ingredients(recipe_database, include_title=False):
    '''Extract ingredients from recipes, returning a dict with links as keys.
       Optionally include titles.'''
    
    recipe_ingredients = {}

    for recipe in recipe_database.values():
        title = []
        parsed_ingredients =  [re.sub(r'\([^)]*\) ', "", parse(ingredient)['name'].lower().split(",")[0]) 
                               for ingredient in recipe['ingredients']]
        
        if include_title == True:
            title = recipe['link'].split('/')[-2].split('-')
        
        recipe_ingredients[recipe['link']] = ' '.join(parsed_ingredients + title)
    
    return recipe_ingredients

def ingredient_tfidf(recipe_ingredients, stemmed_words):
    '''Create a TFIDF sparse matrix across recipes using ingredients.  This is 
       preferred over CountVectorizer because common ingredients like salt should 
       be weighted down'''

    stemmer = LancasterStemmer()
    analyzer = TfidfVectorizer(stop_words='english',min_df=5).build_analyzer()

    def stemmed_words(doc):
        return (stemmer.stem(word) for word in analyzer(doc))

    tfidf = TfidfVectorizer(stop_words='english',min_df=5,analyzer=stemmed_words)
    recipe_tfidf = tfidf.fit_transform(recipe_ingredients.values())
    
    return recipe_tfidf, tfidf


def get_common_words_by_stem(ingredients, stemmer):
    '''Map each stem back to its most common word to verify results'''
    stem_dict = defaultdict(list)
    for ingredient in ingredients:
        stem = stemmer.stem(ingredient)
        stem_dict[stem].append(ingredient)

    for stem,full_names in stem_dict.iteritems():
        counted_names = Counter(full_names)
        stem_dict[stem] = counted_names.most_common(1)[0][0]
        
    return stem_dict

def get_similar_recipes(recipe, recipe_similarity_df, top_n = 5):
	'''Return recipes similar to input'''
    sim_dict = []
    recipe_flavors = recipe_similarity_df.ix[recipe,:]
    for i in recipe_similarity_df.iterrows():
        if i[0] != recipe:
            sim_dict.append({'link':i[0],'sim':1-spatial.distance.cosine(recipe_flavors,i[1])})
    
    top_matches = sorted(sim_dict, key = lambda x: x['sim'], reverse=True)[:top_n]
    
    flavor_dict = [{recipe: dict(recipe_flavors)}]
    for i in top_matches:
        flavor_dict.append({i['link']:dict(recipe_similarity_df.ix[i['link'],:])})

    return top_matches, flavor_dict

recipe_database = fetch_recipes(client.recipe_database_full.rdb)
recipe_ingredients = get_ingredients(recipe_database,include_title=True)
recipe_tfidf, tfidf_transformer = ingredient_tfidf(recipe_ingredients)
stem_dict = get_common_words_by_stem(' '.join(recipe_ingredients.values()).split(), LancasterStemmer())

# Apply NMF to TFIDF, return top words by component

dense_recipe_tfidf = pd.DataFrame(recipe_tfidf.todense(),
                                  columns=[tfidf_transformer.get_feature_names()],
                                  index=recipe_ingredients.keys())

model = decomposition.NMF(init="nndsvd", n_components=20, max_iter=1000)
W = model.fit_transform(dense_recipe_tfidf)
H = model.components_
recipes = dense_recipe_tfidf.index
ingredients = dense_recipe_tfidf.columns

count = 0
for topic_index in range(H.shape[0]):
    count += 1
    top_indices = np.argsort(H[topic_index,:])[::-1][0:10]
    term_ranking = [stem_dict[ingredients[i]] for i in top_indices]
    print "Topic %d: %s" % (topic_index+1, ", ".join(term_ranking))
    if count%5 ==0:
        print(" ")
        
recipe_similarity_df = pd.DataFrame(W, index=recipes, columns = ['topic_' + str(i) for i in range(1,21)])  

top_matches, flavor_dict = get_similar_recipes('/recipe/16440/cornmeal-strawberry-cake/',recipe_similarity_df)      