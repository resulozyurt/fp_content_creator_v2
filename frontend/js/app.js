const { createApp } = Vue;
const app = createApp({
  data() {
    return {
      form: { keyword: "", language: "tr", country: "tr" },
      isLoading: false,
      step: 0,
      articleMarkdown: "",
      summary: null,
      error: null,
      isPublishing: false,
      showIgnored: false,
      nlpMatrix: [],
      seoScore: 0,
      activeTab: 'preview', // Varsayılan sekme artık Preview
      // YAPISAL SEO METRİKLERİ DEĞİŞKENİ EKLENDİ
      structMetrics: { words: 0, h2: 0, h3: 0, kwDensity: 0, images: 0, links: 0 }
    };
  },
  computed: {
    renderedHtml() {
      return this.articleMarkdown ? marked.parse(this.articleMarkdown) : "";
    },
    scoreColor() {
      // Skor rengi toleransı artırıldı (daha mantıklı renklendirme)
      if (this.seoScore < 50) return 'text-red-500';
      if (this.seoScore < 80) return 'text-yellow-500';
      return 'text-green-500';
    }
  },
  watch: {
    articleMarkdown(newVal) {
      if (!this.nlpMatrix || this.nlpMatrix.length === 0) return;
      const text = newVal.toLowerCase();
      
      // 1. NLP (LSI) Skor Hesaplaması
      let nlpTotal = 0;
      let nlpMax = 0;

      this.nlpMatrix.forEach(item => {
        const kw = item.keyword.toLowerCase();
        const regex = new RegExp(`\\b${kw}\\b`, 'gi');
        const matches = text.match(regex);
        item.current_freq = matches ? matches.length : 0;
        
        const weight = item.score_weight;
        nlpMax += weight;
        
        if (item.current_freq > 0) {
          const ratio = Math.min(item.current_freq / item.target_freq, 1);
          nlpTotal += (weight * ratio);
        }
      });
      
      let nlpScore = nlpMax > 0 ? (nlpTotal / nlpMax) * 100 : 0;

      // 2. LLM Yapısal ve Teknik SEO Metriklerinin Kaplanması
      const kwPattern = new RegExp(`\\b${this.form.keyword.toLowerCase()}\\b`, 'gi');
      const kwMatches = text.match(kwPattern);
      const kwCount = kwMatches ? kwMatches.length : 0;
      const words = text.split(/\s+/).filter(w => w.length > 0).length;
      
      this.structMetrics = {
        words: words,
        h2: (newVal.match(/^##\s/gm) || []).length,
        h3: (newVal.match(/^###\s/gm) || []).length,
        kwDensity: words > 0 ? ((kwCount / words) * 100).toFixed(1) : 0,
        images: (newVal.match(/\[IMAGE_/gi) || newVal.match(/<img/gi) || []).length,
        links: (newVal.match(/\]\((http|https):\/\/[^\)]+\)/gi) || []).length
      };

      // 3. Ortak Skor Hesaplama (%60 LSI NLP Skoru, %40 Yapısal Puanlama)
      let structScore = 0;
      if (this.structMetrics.words > 600) structScore += 20; else if (this.structMetrics.words > 300) structScore += 10;
      if (this.structMetrics.h2 >= 3) structScore += 20;
      if (this.structMetrics.h3 >= 2) structScore += 10;
      if (this.structMetrics.images >= 2) structScore += 20;
      if (this.structMetrics.links >= 3) structScore += 15;
      if (this.structMetrics.kwDensity >= 0.5 && this.structMetrics.kwDensity <= 2.5) structScore += 15;

      this.seoScore = Math.round((nlpScore * 0.6) + (Math.min(structScore, 100) * 0.4));
    }
  },
  methods: {
    async generateArticle() {
      this.isLoading = true;
      this.articleMarkdown = "";
      this.summary = null;
      this.error = null;
      this.step = 1;
      this.showIgnored = false;
      this.nlpMatrix = [];
      this.seoScore = 0;
      this.activeTab = 'preview'; // Üretim sonrası Preview'a atar

      setTimeout(() => { if (this.isLoading) this.step = 2; }, 4000);
      setTimeout(() => { if (this.isLoading) this.step = 3; }, 12000);

      try {
        const response = await fetch("/api/v1/auto-create-article", {
  method: "POST",
  headers: { 
    "Content-Type": "application/json",
    ...AuthService.getAuthHeaders() // YENİ EKLENDİ (Güvenlik Kilidi Anahtarı)
  },
  body: JSON.stringify(this.form),
});

        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Bilinmeyen bir hata oluştu");

        this.articleMarkdown = data.final_article;
        this.summary = data.process_summary;
        this.nlpMatrix = data.nlp_matrix || [];
        this.step = 4;
      } catch (err) {
        alert("Hata: " + err.message);
        this.error = err.message;
      } finally {
        this.isLoading = false;
      }
    },
    async copyToClipboard() {
      try {
        await navigator.clipboard.writeText(this.articleMarkdown);
        alert("Markdown içeriği başarıyla kopyalandı!");
      } catch (err) {
        alert("Kopyalama başarısız oldu.");
      }
    },
async publishToWp() {
      // localStorage'den veri çekme kodları TAMAMEN SİLİNDİ
      if (!this.articleMarkdown) {
        alert("Önce bir içerik üretmelisiniz!");
        return;
      }

      this.isPublishing = true;
      const titleMatch = this.articleMarkdown.match(/^#\s+(.*)/m);
      const postTitle = titleMatch ? titleMatch[1] : this.form.keyword;

      // Sadece başlık, içerik ve durumu gönderiyoruz. Şifreler Backend'de DB'den eklenecek!
      const payload = {
        title: postTitle,
        content_markdown: this.articleMarkdown,
        status: 'draft'
      };

      try {
        const response = await fetch("/api/v1/publish-to-wp", {
          method: "POST",
          headers: { 
            "Content-Type": "application/json",
            ...AuthService.getAuthHeaders() // Token gönderimi
          },
          body: JSON.stringify(payload),
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "WP aktarım hatası oluştu.");

        alert(`Başarılı! Makale WordPress'e native Gutenberg blokları olarak aktarıldı.\nYazı ID: ${data.post_id}`);
      } catch (err) {
        // Eğer DB'de ayar yoksa backend bizi buraya düşürecek
        alert("Hata: " + err.message);
        if(err.message.includes("WP Entegrasyonu")) {
             window.location.href = "/wp-settings";
        }
      } finally {
        this.isPublishing = true; // Wait, let's fix this in the code below to false
        this.isPublishing = false;
      }
    }
  },
});

app.component('app-sidebar', AppSidebar);
app.mount("#app");