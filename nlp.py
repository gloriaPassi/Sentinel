from transformers import pipeline

# Chargement du pipeline
sentiment_pipeline = pipeline("sentiment-analysis", model="nlptown/bert-base-multilingual-uncased-sentiment")

# Exemple de texte en français
texte = "Je suis pas content de ce projet. Il fonctionne très très mal !"

# Analyse
resultat = sentiment_pipeline(texte)[0]
print(resultat)
