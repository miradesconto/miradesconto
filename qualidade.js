'use strict';
// Catálogo estático: política de 24h de integracoes/qualidade.py. Observações Edge: máximo 15min.
const MiraQuality = (() => {
    function usablePrice(product, now = Date.now()) {
        const e = product.priceCheck;
        if (product.edgePrice?.status === 'error') return false;
        if (!e || e.status !== 'verified' || !['poly-card-v1', 'ml-sale-price-v1', 'ml-edge-item-v1'].includes(e.method) || e.currency !== 'BRL') return false;
        const expected = e.method === 'ml-sale-price-v1' ? product.itemId : product.id;
        if (!expected || e.itemId !== expected) return false;
        if (typeof product.price !== 'number' || !Number.isFinite(product.price) || product.price <= 0 || product.available === false) return false;
        if (e.price !== product.price || e.oldPrice !== product.oldPrice) return false;
        if (typeof e.checkedAt !== 'string' || !/(Z|[+-]\d{2}:\d{2})$/.test(e.checkedAt)) return false;
        const age = now - Date.parse(e.checkedAt);
        const maxAge = e.method === 'ml-edge-item-v1' ? 15 * 60 * 1000 : 24 * 60 * 60 * 1000;
        return Number.isFinite(age) && age >= 0 && age < (e.method === 'ml-edge-item-v1' ? maxAge : maxAge + 1);
    }
    return {usablePrice};
})();
if (typeof module !== 'undefined') module.exports = MiraQuality;
