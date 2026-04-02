const AuthService = {
    getToken() {
        return localStorage.getItem('access_token');
    },
    setToken(token) {
        localStorage.setItem('access_token', token);
    },
    removeToken() {
        localStorage.removeItem('access_token');
    },
    isAuthenticated() {
        return !!this.getToken();
    },
    logout() {
        this.removeToken();
        window.location.href = '/login';
    },
    getAuthHeaders() {
        const token = this.getToken();
        return token ? { 'Authorization': `Bearer ${token}` } : {};
    }
};

// Sayfa yüklendiğinde Auth kontrolü yap (Login/Register sayfaları hariç)
const currentPath = window.location.pathname;
if (!AuthService.isAuthenticated() && currentPath !== '/login' && currentPath !== '/register') {
    window.location.href = '/login';
}