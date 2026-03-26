const { createApp } = Vue;

// ORTAK MENÜ BİLEŞENİ
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
      wpForm: {
        wp_url: localStorage.getItem('wp_url') || "",
        wp_username: localStorage.getItem('wp_username') || "",
        wp_app_password: localStorage.getItem('wp_app_password') || "",
        status: localStorage.getItem('wp_status') || "draft"
      },
      isSaved: false
    };
  },
  methods: {
    saveSettings() {
      localStorage.setItem('wp_url', this.wpForm.wp_url);
      localStorage.setItem('wp_username', this.wpForm.wp_username);
      localStorage.setItem('wp_app_password', this.wpForm.wp_app_password);
      localStorage.setItem('wp_status', this.wpForm.status);
      
      this.isSaved = true;
      setTimeout(() => { this.isSaved = false; }, 3000);
    }
  }
});

app.component('app-sidebar', AppSidebar);
app.mount("#app");