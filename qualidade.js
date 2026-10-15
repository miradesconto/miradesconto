'use strict';
// Same 2-hour price policy as integracoes/qualidade.py; checked in offline tests.
const MiraQuality = (() => {
    // Conservatively quarantine implausible prices without changing recorded data or links.
    function priceReviewReason(product) {
        const price = product?.price;
        const name = typeof product?.name === 'string' ? product.name : '';
        if (Number.isFinite(price) && price >= 5000
            && /\b(?:smart\s+)?tv\b|\btelevisor\b/i.test(name)
            && /\b43\b/.test(name)
            && /\b(?:full\s*hd|fhd)\b/i.test(name)) return 'tv_43_fhd_above_review_limit';
        return null;
    }
    function usablePrice(product, now = Date.now()) {
        if (priceReviewReason(product)) return false;
        const e = product.priceCheck;
        if (!e || e.status !== 'verified' || !['poly-card-v1', 'ml-sale-price-v1'].includes(e.method) || e.currency !== 'BRL') return false;
        const expected = e.method === 'ml-sale-price-v1' ? product.itemId : product.id;
        if (!expected || e.itemId !== expected) return false;
        if (typeof product.price !== 'number' || !Number.isFinite(product.price) || product.price <= 0 || product.available === false) return false;
        if (e.price !== product.price || e.oldPrice !== product.oldPrice) return false;
        if (typeof e.checkedAt !== 'string' || !/(Z|[+-]\d{2}:\d{2})$/.test(e.checkedAt)) return false;
        const age = now - Date.parse(e.checkedAt);
        return Number.isFinite(age) && age >= 0 && age <= 2 * 60 * 60 * 1000;
    }
    return {usablePrice, priceReviewReason};
})();
// Classic scripts share top-level lexical bindings, but features also read a window property.
if (typeof window !== 'undefined') window.MiraQuality = MiraQuality;
if (typeof module !== 'undefined') module.exports = MiraQuality;
