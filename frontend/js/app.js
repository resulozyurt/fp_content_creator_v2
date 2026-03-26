const { createApp } = Vue;

// MENÜ BİLEŞENİ (Dosya yolu sorununu ortadan kaldırmak için buraya gömüldü)
const AppSidebar = {
  data() {
    return { currentPath: window.location.pathname };
  },
  template: `
    <aside class="w-64 bg-slate-900 text-white flex flex-col hidden md:flex">
      <div class="h-16 flex items-center px-6 border-b border-slate-700">
        <i class="fa-solid fa-bolt text-brand-500 text-xl mr-3"></i>
        <span class="text-lg font-bold tracking-wider">ContentEngine</span>
      </div>
      <nav class="flex-1 px-4 py-6 space-y-2">
        <a href="/" :class="['flex items-center px-4 py-3 rounded-lg transition-colors', currentPath === '/' ? 'bg-brand-600 text-white' : 'text-slate-300 hover:bg-slate-800 hover:text-white']">
          <i class="fa-solid fa-pen-nib w-5 mr-3"></i><span class="font-medium">İçerik Üretici</span>
        </a>
        <a href="/history" :class="['flex items-center px-4 py-3 rounded-lg transition-colors', currentPath === '/history' ? 'bg-brand-600 text-white' : 'text-slate-300 hover:bg-slate-800 hover:text-white']">
          <i class="fa-solid fa-database w-5 mr-3"></i><span class="font-medium">Geçmiş Kayıtlar</span>
        </a>
        <a href="/wp-settings" :class="['flex items-center px-4 py-3 rounded-lg transition-colors', currentPath === '/wp-settings' ? 'bg-brand-600 text-white' : 'text-slate-300 hover:bg-slate-800 hover:text-white']">
          <i class="fa-brands fa-wordpress w-5 mr-3"></i><span class="font-medium">WP Entegrasyonu</span>
        </a>
      </nav>
    </aside>
  `
};

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
      showIgnored: false
    };
  },
  computed: {
    renderedHtml() {
      return this.articleMarkdown ? marked.parse(this.articleMarkdown) : "";
    },
  },
  methods: {
    async generateArticle() {
      this.isLoading = true;
      this.articleMarkdown = "";
      this.summary = null;
      this.error = null;
      this.step = 1;
      this.showIgnored = false;

      setTimeout(() => { if (this.isLoading) this.step = 2; }, 4000);
      setTimeout(() => { if (this.isLoading) this.step = 3; }, 12000);

      try {
        const response = await fetch("/api/v1/auto-create-article", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(this.form),
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Bilinmeyen bir hata oluştu");

        this.articleMarkdown = data.final_article;
        this.summary = data.process_summary;
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
      const wpUrl = localStorage.getItem('wp_url');
      const wpUser = localStorage.getItem('wp_username');
      const wpPass = localStorage.getItem('wp_app_password');
      const wpStatus = localStorage.getItem('wp_status') || 'draft';

      if (!wpUrl || !wpUser || !wpPass) {
        alert("Lütfen önce sol menüden 'WP Entegrasyonu' sayfasına giderek API bilgilerinizi kaydedin.");
        window.location.href = "/wp-settings";
        return;
      }

      if (!this.articleMarkdown) {
        alert("Önce bir içerik üretmelisiniz!");
        return;
      }

      this.isPublishing = true;
      const titleMatch = this.articleMarkdown.match(/^#\s+(.*)/m);
      const postTitle = titleMatch ? titleMatch[1] : this.form.keyword;

      const payload = {
        wp_url: wpUrl,
        wp_username: wpUser,
        wp_app_password: wpPass,
        status: wpStatus,
        title: postTitle,
        content_markdown: this.articleMarkdown
      };

      try {
        const response = await fetch("/api/v1/publish-to-wp", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "WP aktarım hatası oluştu.");

        alert(`Başarılı! Makale WordPress'e native Gutenberg blokları olarak aktarıldı.\nYazı ID: ${data.post_id}`);
      } catch (err) {
        alert("Hata: " + err.message);
      } finally {
        this.isPublishing = false;
      }
    }
  },
});

app.component('app-sidebar', AppSidebar);
app.mount("#app");