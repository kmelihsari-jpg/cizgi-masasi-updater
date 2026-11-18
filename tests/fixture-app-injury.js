// Canli app.js'ten (18 Kasim 2026) alinan, yamanin dokundugu satirlarin birebir kopyalari.
const store={get:k=>null,set:(k,v)=>{}};
let INJPREV=store.get('cm-injprev'),INJOPP=[],INJSEEN=new Set(store.get('cm-injseen')||[]),ACTX=null,INJBAN=[],INJBUSY=false;
let IOWN=false,TEST=false;
function injBeep(){try{ACTX=ACTX||new (window.AudioContext||window.webkitAudioContext)();ACTX.resume&&ACTX.resume();const t=ACTX.currentTime;[0,.22,.44].forEach((d,i)=>{const o=ACTX.createOscillator(),g=ACTX.createGain();o.type='sine';o.frequency.value=i===2?1175:880;g.gain.setValueAtTime(.0001,t+d);g.gain.exponentialRampToValueAtTime(.35,t+d+.02);g.gain.exponentialRampToValueAtTime(.0001,t+d+.18);o.connect(g);g.connect(ACTX.destination);o.start(t+d);o.stop(t+d+.2)})}catch(e){}}
async function injAdd(items,evs){if(TEST)items.forEach(c=>{c.test=true});INJOPP=INJOPP.concat(items);if(!IOWN&&!TEST){try{refreshHomeInj()}catch(e){}return}
  injNotify(items,evs);if(TEST){try{refreshHomeInj()}catch(e){}return}await injPersist(items)}
