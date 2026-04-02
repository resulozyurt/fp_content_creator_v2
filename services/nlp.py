import re
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer

# Kapsamlı Türkçe ve İngilizce Stop-Words (Dolgu Kelimeleri) Listesi Eklendi
STOP_WORDS = [
    "bir", "ve", "ile", "için", "bu", "daha", "olarak", "da", "de", "en", "çok", "gibi", "kadar", "olan", "sonra", "önce", "ya", "veya", "ise", "var", "yok", "nedir", "nasıl", "içinde", "üzere", "bunun", "buna", "bunu", "şekilde", "teknik", "veri", "ilgili", "tüm", "her", "hangi", "göre", "tarafından", "olur", "oldu", "olacak", "yapılır", "yapan", "yapacak", "edilir", "eden", "edecek", "gerekir", "gereken", "gerek", "diğer", "ayrıca", "ancak", "ama", "fakat", "sadece", "tek", "büyük", "küçük", "yeni", "eski", "iyi", "kötü", "genel", "özel", "tam", "kısmi", "ilk", "son", "fazla", "az", "aynı", "farklı", "birlikte", "böyle", "şöyle", "şunu", "bizi", "bize", "bizim", "sizi", "size", "sizin", "onlar", "onları", "onlara", "onların", "burada", "şurada", "orada", "buraya", "şuraya", "oraya", "bugün", "yarın", "dün", "şimdi", "zaman", "yer", "şey", "neden", "niçin", "kim", "kime", "kimde", "kimden", "mi", "mı", "mu", "mü", "şu", "o", "ki", "hem", "hiç", "ne", "niye", "bazı", "belki", "çünkü", "hep", "hiçbir", "kez", "olmak", "yapmak", "etmek", "üzerine", "karşı", "rağmen", "artık", "bile", "kendi", "değil", "arasında", "kısaca", "özellikle", "genellikle", "tamamen", "nedeniyle", "sonucunda", "durumda", "konusunda", "açısından", "dair", "ait", "içerisinde", "doğru", "kapsamında", "halde", "yerine", "the", "and", "is", "in", "to", "of", "it", "that", "for", "on", "with", "as", "this", "by", "are", "be", "at", "or", "from", "an", "was", "we", "can", "us", "if", "has", "but", "all", "what", "about", "which", "when", "one", "their", "there", "would", "how", "more", "out", "up", "so", "some", "only", "do", "you", "they", "will", "have"
]

def clean_text(text: str) -> str:
    """
    Metni NLP analizi için temizler. Özel karakterleri, markdown linklerini
    kaldırır ve küçük harfe çevirir.
    """
    # Markdown linklerini temizle
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Sadece harfleri ve boşlukları bırak
    text = re.sub(r'[^a-zA-ZğüşıöçĞÜŞİÖÇ\s]', '', text)
    return text.lower()

def extract_target_keywords(competitor_data: List[Dict[str, Any]], top_n: int = 15) -> List[Dict[str, Any]]:
    """
    Rakiplerin içeriklerini TF-IDF ile analiz ederek en çok kullanılan
    LSI kelimeleri ve hedef frekanslarını çıkarır.
    """
    documents = [clean_text(item.get("content", "")) for item in competitor_data]
    
    if not documents:
        return []

    # 1 ve 2 kelimelik öbekleri (n-gram) analiz et (STOP_WORDS eklendi)
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_df=0.85, min_df=2, max_features=top_n * 3, stop_words=STOP_WORDS)
    
    try:
        tfidf_matrix = vectorizer.fit_transform(documents)
    except ValueError:
        # Veri seti çok küçükse boş döner
        return []

    feature_names = vectorizer.get_feature_names_out()
    dense = tfidf_matrix.todense()
    episode = dense.tolist()
    
    keyword_scores = {}
    num_docs = len(documents)
    
    for j in range(len(feature_names)):
        keyword = feature_names[j]
        
        # Kelime öbeklerinde stop-word geçiyorsa iptal et (Örn: "veri analiz", "daha iyi")
        if any(word in STOP_WORDS for word in keyword.split()):
            continue
            
        total_score = sum(episode[i][j] for i in range(num_docs))
        
        # Rakip kullanımına göre hedef frekans belirle (minimum 2)
        target_frequency = max(2, int((total_score / num_docs) * 100)) 
        
        keyword_scores[keyword] = {
            "keyword": keyword,
            "target_freq": target_frequency,
            "current_freq": 0,
            "score_weight": round(total_score, 2)
        }

    # Ağırlığa göre sırala ve en iyi sonuçları al
    sorted_keywords = sorted(keyword_scores.values(), key=lambda x: x["score_weight"], reverse=True)[:top_n]
    return sorted_keywords