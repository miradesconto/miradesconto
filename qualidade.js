'use strict';
// Same 24-hour price policy as integracoes/qualidade.py; checked in offline tests.
const MiraQuality = (() => {
    function usablePrice(product, now = Date.now()) {
        const e = product.priceCheck;
        if (!e || e.status !== 'verified' || e.method !== 'poly-card-v1' || e.itemId !== product.id || e.currency !== 'BRL') return false;
        if (typeof product.price !== 'number' || !Number.isFinite(product.price) || product.price <= 0 || product.available === false) return false;
        if (e.price !== product.price || e.oldPrice !== product.oldPrice) return false;
        if (typeof e.checkedAt !== 'string' || !/(Z|[+-]\d{2}:\d{2})$/.test(e.checkedAt)) return false;
        const age = now - Date.parse(e.checkedAt);
        return Number.isFinite(age) && age >= 0 && age <= 24 * 60 * 60 * 1000;
    }
    return {usablePrice};
})();
if (typeof module !== 'undefined') module.exports = MiraQuality;
