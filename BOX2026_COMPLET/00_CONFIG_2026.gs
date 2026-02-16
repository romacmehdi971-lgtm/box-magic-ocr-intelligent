// Déclaration de la configuration en tant qu'objet JavaScript
var config = {
  live_mode: "ON",
  crm_api: {
    mode: "JSONP",
    base_url: "https://script.google.com/macros/s/AKfycbx0sc_XRNZ0sWP2B_W26uZHdcBTd_J_FjpG5Tst3QydHuTdl8Jhj0Nby3kkpJ6H4_oA/exec",
    timeout_ms: 8000
  },
  sources: {
    clients: { entity: "clients" },
    devis: { entity: "devis" },
    factures: { entity: "factures" },
    events: { entity: "events" },
    docs: { use_index_global: true }
  }
};

// Exemple d'utilisation de la configuration
function utiliserConfig() {
  Logger.log("Mode live : " + config.live_mode);
  Logger.log("URL de base de l'API CRM : " + config.crm_api.base_url);
  
  // Exemple d'accès aux sources
  Logger.log("Entité client : " + config.sources.clients.entity);
}

// Appel de la fonction pour tester
utiliserConfig();
