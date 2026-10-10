'use strict';
(() => {
    let base = null;
    const ids = new Set((window.MIRA_DATA?.products || []).map(p => p.id));
    try {
        const raw = window.MIRA_LINK_CONFIG?.goBaseUrl;
        if (typeof raw === 'string' && raw.trim()) {
            const url = new URL(raw.trim());
            const local = ['localhost', '127.0.0.1'].includes(url.hostname);
            if ((url.protocol === 'https:' || (local && url.protocol === 'http:'))
                && !url.username && !url.password && !url.search && !url.hash && url.pathname === '/') base = url;
        }
    } catch { /* Configuração inválida mantém os links oficiais existentes. */ }
    function forProduct(p) {
        if (!base || !p || !/^MLB\d{7,14}$/.test(p.id) || !ids.has(p.id)
            || (p.itemId && p.itemId !== p.id)) return null;
        return new URL('/go/' + p.id, base).href;
    }
    function isGoLink(href) {
        if (!base) return false;
        try {
            const url = new URL(href, window.location.href);
            const match = /^\/go\/(MLB\d{7,14})$/.exec(url.pathname);
            return url.origin === base.origin && !url.username && !url.password && !url.search && !url.hash
                && Boolean(match && ids.has(match[1]));
        } catch {return false;}
    }
    window.MiraLinks = Object.freeze({enabled: Boolean(base), forProduct, isGoLink});
})();
