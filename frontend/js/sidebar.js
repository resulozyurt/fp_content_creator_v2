const AppSidebar = {
    data() {
        return {
            currentPath: window.location.pathname,
            userRole: 'user', // Varsayılan rol
            menuItems: [
                { path: '/', icon: 'fa-solid fa-pen-nib', text: 'SEO İçerik Üretici', show: true },
                { path: '/history', icon: 'fa-solid fa-database', text: 'Geçmiş Kayıtlar', show: true },
                { path: '/wp-settings', icon: 'fa-brands fa-wordpress', text: 'WP Entegrasyonu', show: true },
                // İleride eklenecek modüller
                { path: '#1', icon: 'fa-regular fa-envelope', text: 'Newsletter Modülü', show: true, disabled: true },
                { path: '#2', icon: 'fa-solid fa-hashtag', text: 'Sosyal Medya Modülü', show: true, disabled: true },
            ]
        };
    },
    async mounted() {
        try {
            const res = await fetch('/api/auth/me', { headers: AuthService.getAuthHeaders() });
            if (res.ok) {
                const data = await res.json();
                this.userRole = data.role;
            }
        } catch (err) {
            console.error("Kullanıcı yetkisi alınamadı:", err);
        }
    },
    methods: {
        logout() {
            AuthService.logout();
        },
        isActive(path) {
            // URL eşleştirme mantığını güçlendiriyoruz (Sondaki slash'leri vb. yoksayar)
            const current = this.currentPath.replace(/\/$/, '') || '/';
            const target = path.replace(/\/$/, '') || '/';
            return current === target;
        }
    },
    template: `
      <aside class="w-64 bg-slate-900 text-white flex flex-col hidden md:flex h-screen sticky top-0 shrink-0 shadow-xl">
        <div class="h-16 flex items-center px-6 border-b border-slate-700 bg-slate-950/50">
          <i class="fa-solid fa-bolt text-brand-500 text-xl mr-3"></i>
          <span class="text-lg font-bold tracking-wider">ContentEngine</span>
        </div>
        
        <nav class="flex-1 flex flex-col px-4 py-6 overflow-y-auto">
          <div class="space-y-2 flex-1">
              <template v-for="item in menuItems" :key="item.text">
                  <a v-if="!item.disabled" :href="item.path" :class="['flex items-center px-4 py-3 rounded-lg transition-colors', isActive(item.path) ? 'bg-brand-600 text-white shadow-lg shadow-brand-500/30' : 'text-slate-300 hover:bg-slate-800 hover:text-white']">
                    <i :class="[item.icon, 'w-5 mr-3']"></i><span class="font-medium">{{ item.text }}</span>
                  </a>
                  <div v-else class="flex items-center px-4 py-3 rounded-lg text-slate-500 opacity-50 cursor-not-allowed bg-slate-800/30 border border-slate-800 border-dashed mt-4" title="Yakında eklenecek">
                    <i :class="[item.icon, 'w-5 mr-3']"></i>
                    <div class="flex flex-col">
                        <span class="font-medium text-sm">{{ item.text }}</span>
                        <span class="text-[10px] uppercase tracking-wider text-brand-400 mt-0.5">Yakında</span>
                    </div>
                  </div>
              </template>
          </div>
          
          <div class="mt-8 pt-6 border-t border-slate-700 space-y-2">
              <a v-if="userRole === 'admin'" href="/admin" :class="['flex items-center px-4 py-3 rounded-lg transition-colors mb-2 border', isActive('/admin') ? 'bg-purple-600 text-white border-purple-500 shadow-lg shadow-purple-500/30' : 'text-purple-400 hover:bg-slate-800 hover:text-purple-300 border-purple-900/50']">
                  <i class="fa-solid fa-shield-halved w-5 mr-3"></i><span class="font-medium">Admin Panel</span>
              </a>
              
              <button @click="logout" class="w-full flex items-center px-4 py-3 rounded-lg text-slate-400 hover:bg-red-900/30 hover:text-red-400 transition-colors">
                  <i class="fa-solid fa-right-from-bracket w-5 mr-3"></i><span class="font-medium">Çıkış Yap</span>
              </button>
          </div>
        </nav>
      </aside>
    `
};