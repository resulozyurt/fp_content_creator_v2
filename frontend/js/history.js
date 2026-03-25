// frontend/js/history.js
const { createApp } = Vue;

createApp({
  data() {
    return {
      history: [],
      isLoading: true,
      selectedArticle: null,
      isPublishing: false
    };
  },
  computed: {
    renderedModalHtml() {
      return this.selectedArticle ? marked.parse(this.selectedArticle.article_markdown) : "";
    }
  },
  mounted() {
    this.fetchHistory();
  },
  methods: {
    async fetchHistory() {
      try {
        const response = await fetch("/api/v1/history");
        const data = await response.json();
        this.history = data;
      } catch (error) {
        alert("Geçmiş veriler yüklenirken hata oluştu.");
      } finally {
        this.isLoading = false;
      }
    },
    formatDate(dateString) {
      const date = new Date(dateString);
      return date.toLocaleDateString('tr-TR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute:'2-digit' });
    },
    viewArticle(item) {
      this.selectedArticle = item;
    },
    async publishToWp(articleData) {
      const wpUrl = localStorage.getItem('wp_url');
      const wpUser = localStorage.getItem('wp_username');
      const wpPass = localStorage.getItem('wp_app_password');
      const wpStatus = localStorage.getItem('wp_status') || 'draft';

      if (!wpUrl || !wpUser || !wpPass) {
        alert("Lütfen önce sol menüden 'WP Entegrasyonu' sayfasına giderek API bilgilerinizi kaydedin.");
        window.location.href = "/wp-settings";
        return;
      }

      this.isPublishing = true;
      const titleMatch = articleData.article_markdown.match(/^#\s+(.*)/m);
      const postTitle = titleMatch ? titleMatch[1] : articleData.keyword;

      const payload = {
        wp_url: wpUrl,
        wp_username: wpUser,
        wp_app_password: wpPass,
        status: wpStatus,
        title: postTitle,
        content_markdown: articleData.article_markdown
      };

      try {
        const response = await fetch("/api/v1/publish-to-wp", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "WP aktarım hatası oluştu.");

        alert(`Başarılı! Geçmiş makale WordPress'e aktarıldı.\nYazı ID: ${data.post_id}`);
      } catch (err) {
        alert("Hata: " + err.message);
      } finally {
        this.isPublishing = false;
      }
    }
  }
}).mount("#app");