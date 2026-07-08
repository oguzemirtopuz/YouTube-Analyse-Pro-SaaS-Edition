/**
 * background.js — YT Analiz Pro | Viral Klonlama Motoru
 * Manifest V3 Service Worker
 *
 * Eklenti ikonuna tıklandığında popup.html'i yeni sekmede tam ekran açar.
 */

chrome.runtime.onInstalled.addListener(({ reason }) => {
  if (reason === 'install') {
    console.log('[YT Analiz Pro] Eklenti kuruldu. Viral Klonlama Motoru hazır.');
  }
});

// Eklenti ikonuna tıklandığında yeni sekmede tam ekran aç
// (manifest.json'dan default_popup kaldırıldığı için bu event çalışır)
chrome.action.onClicked.addListener(async (tab) => {
  const ytUrl = tab && tab.url ? tab.url : '';
  const popupUrl = chrome.runtime.getURL('popup.html') + '?url=' + encodeURIComponent(ytUrl);
  chrome.tabs.create({ url: popupUrl });
});
