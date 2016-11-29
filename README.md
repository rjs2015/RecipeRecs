## RecipeRecs

RecipeRecs takes recipes from allrecipes.com and recommends similar recipes based on ingredients.

The app is based on applying NLP to recipe ingredients, where ingredients are treated as words, and analyzed using NMF to determine underlying "ingredient/flavor categories" of which recipes are composed.

After scraping allrecipes.com, data is stored in MongoDB.  The model is applied to this data, as well as the user input in the app, allowing recipes to be compared on the same componenets.

Give it a try!
