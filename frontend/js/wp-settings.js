// frontend/js/wp-settings.js
const { createApp } = Vue;

createApp({
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
}).mount("#app");