import copy, json, unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import Mock,patch
import requests
from integracoes.social import telegram_publisher as tp

NOW=datetime(2026,10,10,1,tzinfo=timezone.utc)
ID='MLB4408547152'
TOKEN='123456789:'+'x'*32
ENTRY={'variationId':None,'baseUrl':'https://www.mercadolivre.com.br/item','search':'?matt_tool=29904275','hash':''}

def product():
    return {'id':ID,'name':'Notebook Acer <Oferta> & Ryzen','price':1000,'oldPrice':1500,'category':'Notebooks','available':None,'availabilityStatus':'unknown',
        'imageUrl':'https://http2.mlstatic.com/official.webp',
        'priceCheck':{'status':'verified','method':'poly-card-v1','itemId':ID,'currency':'BRL','price':1000,'oldPrice':1500,'variationId':None,'checkedAt':NOW.isoformat()}}
def radar():
    return {'generatedAt':NOW.isoformat(),'byId':{ID:{'currentPrice':1000,'checkedAt':NOW.isoformat(),'actionable':True,'averagePrice':1200,'minimumPrice':1000,'spanDays':15,'observations':60}}}
def response(data,status=200):
    return Mock(status_code=status,json=Mock(return_value=data))

class TelegramPublisherTests(unittest.TestCase):
    def test_select_fresh_exact_offer(self):
        self.assertIsNotNone(tp.select_offer([product()],radar(),{ID:ENTRY},NOW))
    def test_skip_stale_unverified_unavailable_or_mismatched(self):
        for field,value in [('available',False),('price',999),('category','Moda')]:
            p=product();p[field]=value
            if field=='category': p['name']='Camiseta algodão'
            self.assertIsNone(tp.select_offer([p],radar(),{ID:ENTRY},NOW))
        self.assertIsNone(tp.select_offer([product()],radar(),{ID:ENTRY},NOW+timedelta(hours=3)))
        r=radar();r['byId'][ID]['currentPrice']=900
        self.assertIsNone(tp.select_offer([product()],r,{ID:ENTRY},NOW))
        e={**ENTRY,'variationId':'123'}
        self.assertIsNone(tp.select_offer([product()],radar(),{ID:e},NOW))
    def test_skip_stale_radar_and_non_actionable(self):
        r=radar();r['generatedAt']=(NOW-timedelta(hours=7)).isoformat()
        self.assertIsNone(tp.select_offer([product()],r,{ID:ENTRY},NOW))
        r=radar();r['byId'][ID]['actionable']=False
        self.assertIsNone(tp.select_offer([product()],r,{ID:ENTRY},NOW))
    def test_caption_html_and_internal_link(self):
        post=tp.build_post(product(),radar()['byId'][ID],'https://worker.example')
        self.assertEqual(post['method'],'sendPhoto');text=post['body']['caption']
        self.assertIn('&lt;Oferta&gt; &amp;',text);self.assertIn('https://worker.example/go/'+ID,text)
        self.assertNotIn('meli.la',text);self.assertNotIn('1500',text)
        self.assertLess(len(text.encode('utf-16-le'))//2,1024)
    def test_text_only_and_untrusted_image(self):
        for p,flag in [(product(),True),({**product(),'imageUrl':'https://evil.test/image.jpg'},False)]:
            self.assertEqual(tp.build_post(p,radar()['byId'][ID],'https://worker.example',flag)['method'],'sendMessage')
    def test_invalid_origins(self):
        for base in ['http://example.com','https://x.test/path','https://user:pass@x.test','https://x.test?key=1']:
            with self.assertRaises(tp.PublishError): tp.origin(base)
    def test_telegram_success_receipt(self):
        session=Mock();session.post.return_value=response({'ok':True,'result':{'message_id':88,'chat':{'id':-100123}}})
        client=tp.TelegramClient(TOKEN,session)
        self.assertEqual(client.send('sendMessage',{'text':'ok'},-100123),{'status':'sent','messageId':88})
        self.assertFalse(session.post.call_args.kwargs['allow_redirects'])
        self.assertNotIn('allow_paid_broadcast',session.post.call_args.kwargs['json'])
    def test_telegram_timeout_is_uncertain_no_retry_or_token_log(self):
        session=Mock();session.post.side_effect=requests.Timeout(TOKEN)
        client=tp.TelegramClient(TOKEN,session)
        self.assertEqual(client.send('sendPhoto',{},-100123),{'status':'uncertain'})
        self.assertEqual(session.post.call_count,1)
    def test_telegram_rejection_and_server_error(self):
        session=Mock();client=tp.TelegramClient(TOKEN,session)
        for status,body,outcome in [(400,{'ok':False,'error_code':400},'rejected'),(429,{'ok':False,'error_code':429},'rejected'),(500,{'ok':False,'error_code':500},'uncertain'),(302,{},'uncertain'),(200,{'ok':True,'result':{'message_id':88,'chat':{'id':1}}},'uncertain')]:
            session.post.return_value=response(body,status)
            self.assertEqual(client.send('sendMessage',{},-100123)['status'],outcome)
    def test_telegram_invalid_json_uncertain(self):
        session=Mock();session.post.return_value=Mock(json=Mock(side_effect=ValueError()))
        self.assertEqual(tp.TelegramClient(TOKEN,session).send('sendMessage',{},1)['status'],'uncertain')
    def test_preflight_channel_and_permission(self):
        client=tp.TelegramClient(TOKEN);client.read=Mock(side_effect=[{'id':1,'is_bot':True},{'id':-100123,'type':'channel'},{'status':'administrator','can_post_messages':True}])
        self.assertEqual(client.preflight('@channel'),-100123)
        client.read=Mock(side_effect=[{'id':1,'is_bot':True},{'id':-100123,'type':'channel'},{'status':'member'}])
        with self.assertRaises(tp.PublishError):client.preflight('@channel')
    def test_state_failure_prevents_send(self):
        state=Mock();state.call.side_effect=tp.PublishError('offline');tg=Mock();tg.preflight.return_value=-100123
        with patch.object(tp,'verify_redirect'),self.assertRaises(tp.PublishError):
            tp.publish(tp.build_post(product(),radar()['byId'][ID],'https://worker.example',True),state,tg,'@channel',ENTRY)
        tg.send.assert_not_called()
    def test_duplicate_prevents_send(self):
        state=Mock();state.call.return_value={'claimed':False,'reason':'daily_limit'};tg=Mock();tg.preflight.return_value=-100123
        with patch.object(tp,'verify_redirect'):
            result=tp.publish(tp.build_post(product(),radar()['byId'][ID],'https://worker.example',True),state,tg,'@channel',ENTRY)
        self.assertFalse(result['posted']);tg.send.assert_not_called()
    def test_reserve_send_finish_order(self):
        order=[];state=Mock();tg=Mock();tg.preflight.return_value=-100123
        state.call.side_effect=lambda action,body: order.append(action) or ({'claimed':True,'id':'reservation'} if action=='claim' else {'saved':True})
        tg.send.side_effect=lambda *a: order.append('send') or {'status':'sent','messageId':88}
        with patch.object(tp,'verify_redirect'):
            result=tp.publish(tp.build_post(product(),radar()['byId'][ID],'https://worker.example',True),state,tg,'@channel',ENTRY)
        self.assertEqual(order,['claim','send','finish']);self.assertTrue(result['posted'])
    def test_uncertain_send_is_recorded_without_fallback(self):
        state=Mock();state.call.side_effect=[{'claimed':True,'id':'reservation'},{'saved':True}];tg=Mock();tg.preflight.return_value=-100123;tg.send.return_value={'status':'uncertain'}
        with patch.object(tp,'verify_redirect'),self.assertRaises(tp.PublishError):
            tp.publish(tp.build_post(product(),radar()['byId'][ID],'https://worker.example',True),state,tg,'@channel',ENTRY)
        self.assertEqual(tg.send.call_count,1);self.assertEqual(state.call.call_args.args[1]['status'],'uncertain')
    def test_bad_redirect_blocks_reservation(self):
        session=Mock();session.get.return_value=Mock(status_code=302,headers={'Location':'https://evil.test'})
        with self.assertRaises(tp.PublishError):tp.verify_redirect({'link':'https://worker.example/go/'+ID},ENTRY,session)
    def test_state_error_redacted(self):
        session=Mock();session.post.side_effect=requests.Timeout('secret'*10)
        with self.assertRaises(tp.PublishError) as cm: tp.StateClient('https://worker.example','secret'*10,session).call('claim',{})
        self.assertNotIn('secret',str(cm.exception));self.assertEqual(session.post.call_count,1)

    def test_receipt_failure_does_not_repeat_telegram(self):
        state=Mock();state.call.side_effect=[{'claimed':True,'id':'reservation'},tp.PublishError('offline')]
        tg=Mock();tg.preflight.return_value=-100123;tg.send.return_value={'status':'sent','messageId':88}
        with patch.object(tp,'verify_redirect'),self.assertRaises(tp.PublishError):
            tp.publish(tp.build_post(product(),radar()['byId'][ID],'https://worker.example',True),state,tg,'@channel',ENTRY)
        self.assertEqual(tg.send.call_count,1)
    def test_dry_run_no_network_or_draft_creation(self):
        from integracoes.social import gerar_pauta as gp
        with patch.object(gp,'load_catalog',return_value={'products':[product()]}),patch.object(gp,'load_radar',return_value=radar()),patch.object(tp,'datetime') as clock,patch.dict(tp.os.environ,{'MIRA_GO_BASE_URL':'https://worker.example'},clear=True),patch.object(tp.requests,'Session') as session:
            clock.now.return_value=NOW;clock.fromisoformat.side_effect=datetime.fromisoformat
            result=tp.run(['--dry-run'])
        self.assertTrue(result['dryRun']);session.assert_not_called()
    def test_invalid_numeric_history_is_rejected(self):
        for key,value in [('spanDays',float('nan')),('observations',True),('minimumPrice',2000)]:
            r=radar();r['byId'][ID][key]=value
            self.assertIsNone(tp.select_offer([product()],r,{ID:ENTRY},NOW))

    def test_check_does_not_require_fresh_offer_or_send(self):
        with patch.object(tp,'TelegramClient') as telegram,patch.object(tp,'verify_redirect') as redirect,patch.object(tp,'select_offer') as select,patch.dict(tp.os.environ,{'MIRA_GO_BASE_URL':'https://worker.example'},clear=True):
            result=tp.run(['--check'])
        self.assertTrue(result['checked']);telegram.return_value.send.assert_not_called();select.assert_not_called();redirect.assert_called_once()

    def test_webp_converts_to_jpeg_before_send(self):
        import io
        from PIL import Image
        raw=io.BytesIO();Image.new('RGB',(32,24),'white').save(raw,format='WEBP')
        session=Mock();session.get.return_value=Mock(status_code=200,iter_content=Mock(return_value=[raw.getvalue()]))
        post=tp.build_post(product(),radar()['byId'][ID],'https://worker.example')
        prepared,photo=tp.prepare_photo(post,session)
        self.assertEqual(prepared['method'],'sendPhoto');self.assertTrue(photo.startswith(b'\xff\xd8'))
        with Image.open(io.BytesIO(photo)) as img: self.assertEqual(img.size,(32,24))
        self.assertFalse(session.get.call_args.kwargs['allow_redirects'])
    def test_image_failure_falls_back_before_telegram(self):
        session=Mock();session.get.side_effect=requests.Timeout('offline')
        post=tp.build_post(product(),radar()['byId'][ID],'https://worker.example')
        prepared,photo=tp.prepare_photo(post,session)
        self.assertEqual(prepared['method'],'sendMessage');self.assertIsNone(photo);self.assertNotIn('photo',prepared['body'])
    def test_send_photo_multipart_does_not_expose_remote_url(self):
        session=Mock();session.post.return_value=response({'ok':True,'result':{'message_id':88,'chat':{'id':-100123}}})
        client=tp.TelegramClient(TOKEN,session)
        self.assertEqual(client.send('sendPhoto',{'caption':'ok','photo':'https://http2.mlstatic.com/image.webp','reply_markup':{'inline_keyboard':[]}},-100123,photo=b'jpeg')['status'],'sent')
        kwargs=session.post.call_args.kwargs
        self.assertEqual(kwargs['files']['photo'][0],'offer.jpg');self.assertNotIn('photo',kwargs['data']);self.assertNotIn('json',kwargs)

    def test_duplicate_key_normalizes_price_and_ignores_collection_time(self):
        p=product();r=radar()['byId'][ID]
        first=tp.build_post(p,r,'https://worker.example')['fingerprint']
        p['price']=1000.0;p['priceCheck']['checkedAt']=(NOW+timedelta(hours=1)).isoformat()
        self.assertEqual(first,tp.build_post(p,r,'https://worker.example')['fingerprint'])

if __name__=='__main__': unittest.main()
