'use strict';
// Consulta exclusivamente o Worker; nunca chama api.mercadolibre.com no navegador.
window.MiraPrices = (() => {
    const nextCheck = new Map();
    const busy = new Set();
    const positive = n => typeof n === 'number' && Number.isFinite(n) && n > 0;
    let endpoint = null;
    try {
        const base = window.MIRA_PRICE_CONFIG?.apiBaseUrl;
        if (base) {
            const url = new URL(base);
            if (url.protocol === 'https:' || (url.protocol === 'http:' && ['localhost','127.0.0.1'].includes(url.hostname))) {
                url.pathname = '/api/prices'; url.search = ''; url.hash = '';
                endpoint = url.href;
            }
        }
    } catch { /* configuração inválida: manter operação estática */ }

    function usableResult(p, data, now) {
        const age = now - Date.parse(data?.checkedAt);
        const expectedVariation = p.priceCheck?.variationId ?? null;
        return data?.id === p.id && data.itemId === p.id && data.currency === 'BRL'
            && data.method === 'ml-edge-item-v1'
            && String(data.variationId ?? '') === String(expectedVariation ?? '')
            && typeof data.checkedAt === 'string' && /Z$/.test(data.checkedAt)
            && Number.isFinite(age) && age >= -30000 && age < 900000
            && (data.available === false || (positive(data.price)
                && (data.oldPrice === null || (positive(data.oldPrice) && data.oldPrice > data.price))));
    }

    function markError(p, code, seconds = 60) {
        // Preservar valor e checkedAt originais: falha não equivale a nova verificação.
        p.edgePrice = {status: 'error', error: code};
        nextCheck.set(p.id, Date.now() + Math.max(60, Math.min(3600, seconds)) * 1000);
    }

    async function requestBatch(batch) {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 20000);
        try {
            const url = new URL(endpoint);
            url.searchParams.set('ids', batch.map(p => p.id).sort().join(','));
            const response = await fetch(url.href, {signal: controller.signal, cache: 'no-store', credentials: 'omit'});
            if (!response.ok) throw new Error('WORKER_HTTP_' + response.status);
            const result = await response.json();
            if (!Array.isArray(result.items)) throw new Error('WORKER_INVALID_RESPONSE');
            const byId = new Map(result.items.map(item => [item.id, item]));
            for (const p of batch) {
                const item = byId.get(p.id), now = Date.now();
                if (item?.code !== 200 || !usableResult(p, item.data, now)) {
                    markError(p, item?.error?.code || 'PRICE_NOT_CONFIRMED', item?.error?.retryAfterSeconds || 60);
                    continue;
                }
                const data = item.data;
                p.edgePrice = {status: data.available === false ? 'unavailable' : 'verified', cache: item.cache};
                p.available = data.available;
                p.availabilityStatus = data.availabilityStatus;
                if (data.available !== false) {
                    // Atualizar apenas preço/evidência do MESMO anúncio. Não alterar URLs ou identidade.
                    p.price = data.price; p.oldPrice = data.oldPrice; p.itemId = p.id;
                    p.discount = data.oldPrice ? (1 - data.price / data.oldPrice) * 100 : null;
                    p.priceSource = data.method;
                    p.priceCheck = {status: 'verified', method: data.method, itemId: data.itemId,
                        variationId: data.variationId, currency: data.currency, checkedAt: data.checkedAt,
                        price: data.price, oldPrice: data.oldPrice};
                }
                // SWR: consultar novamente em 1 minuto para receber a revalidação já concluída.
                const due = item.cache === 'STALE' ? now + 60000 : Date.parse(data.checkedAt) + 600000;
                nextCheck.set(p.id, Math.max(now + 60000, due));
            }
        } catch (error) {
            for (const p of batch) markError(p, error.message || 'WORKER_UNAVAILABLE', 300);
        } finally {
            clearTimeout(timer);
            for (const p of batch) busy.delete(p.id);
            window.dispatchEvent(new Event('mira:prices-updated'));
        }
    }

    async function refresh(candidates) {
        if (!endpoint || document.hidden) return;
        const now = Date.now();
        const selected = [...new Map(candidates.filter(p => /^MLB\d{7,14}$/.test(p.id)).map(p => [p.id, p])).values()]
            .filter(p => !busy.has(p.id) && (nextCheck.get(p.id) || 0) <= now);
        // Marcar todos antes de await: eventos/filtros simultâneos não duplicam consultas.
        selected.forEach(p => busy.add(p.id));
        for (let i = 0; i < selected.length; i += 20) await requestBatch(selected.slice(i, i + 20));
    }
    return {enabled: Boolean(endpoint), refresh};
})();
