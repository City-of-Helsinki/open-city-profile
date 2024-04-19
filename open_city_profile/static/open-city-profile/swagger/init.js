var url = document.currentScript.dataset.url;

window.onload = () => {
  window.ui = SwaggerUIBundle({
    url: url,
    dom_id: '#swagger-ui',
    supportedSubmitMethods: [],
  });
};
