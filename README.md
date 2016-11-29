## RecipeRecs

RecipeRecs takes recipes from allrecipes.com and recommends similar recipes based on ingredients.

This project applies NLP to recipe ingredients, where ingredients are treated as words, and analyzed using NMF to determine underlying "ingredient/flavor categories" of which recipes are composed.

After scraping allrecipes.com, data is stored in MongoDB.  The model is applied to this data, as well as the user input in the app, returning the recipes most similar to the input.

Give it a try!
