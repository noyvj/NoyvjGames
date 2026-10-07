(function(){
  if(window.__cs) return;
  const cv=document.createElement('canvas');cv.width=cv.height=1;const cx=cv.getContext('2d',{willReadFrequently:true});
  function parse(c){
    if(!c||c==='transparent') return {r:0,g:0,b:0,a:0};
    let m=c.match(/^rgba?\(([^)]+)\)$/);
    if(m){const p=m[1].split(/[,\s\/]+/).filter(Boolean).map(parseFloat);return {r:p[0],g:p[1],b:p[2],a:p.length>3?p[3]:1};}
    cx.clearRect(0,0,1,1);cx.fillStyle='rgba(0,0,0,0)';try{cx.fillStyle=c;}catch(e){return {r:0,g:0,b:0,a:0};}
    cx.fillRect(0,0,1,1);const d=cx.getImageData(0,0,1,1).data;return {r:d[0],g:d[1],b:d[2],a:d[3]/255};
  }
  const TOK=/(rgba?\([^)]*\)|color\([^)]*\)|oklab\([^)]*\)|oklch\([^)]*\)|lab\([^)]*\)|lch\([^)]*\)|hsla?\([^)]*\))/gi;
  function stops(bi){const out=[];let m;TOK.lastIndex=0;while((m=TOK.exec(bi))) out.push(parse(m[1]));return out;}
  function selOf(el){
    const parts=[];for(let e=el,i=0;e&&e!==document.body&&i<4;e=e.parentElement,i++){let s=e.tagName.toLowerCase();if(e.id)s+='#'+e.id;else if(e.classList.length)s+='.'+[...e.classList].slice(0,2).join('.');parts.unshift(s);if(e.id)break;}
    return parts.join(' > ');
  }
  function sig(el){const p=el.parentElement;return el.tagName+'.'+[...el.classList].sort().join('.')+'<'+(p?p.tagName+'.'+[...p.classList].sort().join('.'):'')+(el.id&&/-\d+$/.test(el.id)?'':'#'+(el.id||'')) ;}
  function visibleChain(el){
    for(let e=el;e&&e!==document.documentElement;e=e.parentElement){const s=getComputedStyle(e);if(s.display==='none'||e.hidden||parseFloat(s.opacity)===0) return false;if(s.visibility==='hidden') return false;}
    return true;
  }
  function chainOpacity(el){let o=1;for(let e=el;e;e=e.parentElement){o*=parseFloat(getComputedStyle(e).opacity);}return o;}
  function clipRects(el){
    const rs=[{l:0,t:0,r:innerWidth,b:innerHeight}];
    for(let e=el.parentElement;e&&e!==document.documentElement;e=e.parentElement){
      const s=getComputedStyle(e);
      if(s.overflowX!=='visible'||s.overflowY!=='visible'||s.clipPath!=='none'){const r=e.getBoundingClientRect();rs.push({l:r.left,t:r.top,r:r.right,b:r.bottom});}
    }
    return rs;
  }
  function textRects(el){
    const out=[];
    if(el.tagName==='INPUT'||el.tagName==='TEXTAREA'||el.tagName==='SELECT'){const r=el.getBoundingClientRect();const cs=getComputedStyle(el);
      out.push({l:r.left+parseFloat(cs.paddingLeft||0)+2,t:r.top+parseFloat(cs.paddingTop||0)+1,r:r.right-parseFloat(cs.paddingRight||0)-2,b:r.bottom-parseFloat(cs.paddingBottom||0)-1});return out;}
    for(const n of el.childNodes){if(n.nodeType!==3||!n.textContent.trim()) continue;const rg=document.createRange();rg.selectNodeContents(n);for(const r of rg.getClientRects()){if(r.width>0&&r.height>0) out.push({l:r.left,t:r.top,r:r.right,b:r.bottom});}}
    return out;
  }
  let nextId=1;
  window.__cs={
    collect(seen){
      const items=[],pending=[];let disabledSkipped=0,occluded=0;
      for(const el of document.querySelectorAll('body *')){
        const tn=el.tagName;
        if(['SCRIPT','STYLE','NOSCRIPT','svg','path','CANVAS','OPTION'].includes(tn)) continue;
        let text='';
        if(tn==='INPUT'||tn==='TEXTAREA'){ if(['checkbox','radio','button','hidden','range','file','color'].includes(el.type)) continue; text=el.value||el.placeholder||''; }
        else if(tn==='SELECT'){ text=el.options[el.selectedIndex]?el.options[el.selectedIndex].text:''; }
        else { for(const n of el.childNodes){if(n.nodeType===3) text+=n.textContent;} }
        text=text.trim();
        if(!text||!/[A-Za-z0-9]/.test(text)) continue;
        if(!visibleChain(el)) continue;
        { const dt=el.closest('details'); if(dt&&!dt.open){ const sm=el.closest('summary'); if(!(sm&&sm.parentElement===dt)) continue; } }
        const cs=getComputedStyle(el);
        const rects=textRects(el);if(!rects.length) continue;
        if(el.disabled||el.closest('button:disabled,fieldset:disabled')||el.getAttribute('aria-disabled')==='true'){disabledSkipped++;continue;}
        if(!el.dataset.csId) el.dataset.csId=String(nextId++);
        const id=el.dataset.csId;
        if(seen[id]) continue;
        const clips=clipRects(el);
        // visible fraction
        let area=0,vis=0;const vr=[];
        for(const r of rects){const a=(r.r-r.l)*(r.b-r.t);area+=a;let l=r.l,t=r.t,rr=r.r,b=r.b;for(const c of clips){l=Math.max(l,c.l);t=Math.max(t,c.t);rr=Math.min(rr,c.r);b=Math.min(b,c.b);}
          if(rr-l>1&&b-t>1){vis+=(rr-l)*(b-t);vr.push({l,t,r:rr,b});}}
        const base={id,sig:sig(el),sel:selOf(el),text:text.slice(0,40)};
        if(vis<area*0.6||!vr.length){pending.push(base);continue;}
        // occlusion
        const c=vr[0];const hit=document.elementsFromPoint((c.l+c.r)/2,(c.t+c.b)/2);
        if(hit.length&&!el.contains(hit[0])&&!hit[0].contains(el)&&getComputedStyle(el).pointerEvents!=='none'){
          // is it covered by something unrelated?
          if(!hit.slice(0,3).some(h=>el.contains(h)||h.contains(el)) ){occluded++;seen[id]=1;continue;}
          if(!el.contains(hit[0])&&!hit[0].contains(el)){occluded++;seen[id]=1;continue;}
        }
        const clip=cs.webkitBackgroundClip==='text'||cs.backgroundClip==='text';
        let fg=[];
        if(clip){fg=stops(cs.backgroundImage);if(!fg.length){const bc=parse(cs.backgroundColor);if(bc.a>0)fg=[bc];}}
        if(!fg.length){
          let fc=cs.webkitTextFillColor&&cs.webkitTextFillColor!==''?cs.webkitTextFillColor:cs.color;
          let col=parse(fc);
          if((tn==='INPUT')&&!el.value&&el.placeholder) col=parse(getComputedStyle(el,'::placeholder').color);
          fg=[col];
        }
        const fs=parseFloat(cs.fontSize),fw=parseInt(cs.fontWeight)||400;
        items.push({...base,rects:vr,fg,op:chainOpacity(el),large:fs>=24||(fs>=18.66&&fw>=700),clip});
      }
      return {items,pending,disabledSkipped,occluded};
    },
    hide(on){
      let st=document.getElementById('__cs_hide');
      if(on){ if(!st){st=document.createElement('style');st.id='__cs_hide';document.head.appendChild(st);}
        st.textContent='*,*::before,*::after{color:transparent !important;-webkit-text-fill-color:transparent !important;text-shadow:none !important;caret-color:transparent !important;-webkit-text-stroke:0 !important} ::placeholder{color:transparent !important} [data-cs-clip]{background-image:none !important} *{transition:none !important;animation:none !important}';
        document.querySelectorAll('*').forEach(e=>{const s=getComputedStyle(e);});
      } else if(st) st.remove();
    },
    markClip(ids){document.querySelectorAll('[data-cs-id]').forEach(e=>{if(ids.includes(e.dataset.csId)) e.setAttribute('data-cs-clip','1');});},
    unmarkClip(){document.querySelectorAll('[data-cs-clip]').forEach(e=>e.removeAttribute('data-cs-clip'));},
    scrollTo(id){document.documentElement.style.scrollBehavior='auto';document.body.style.scrollBehavior='auto';const e=document.querySelector('[data-cs-id="'+id+'"]');if(e){e.scrollIntoView({block:'center',inline:'center',behavior:'instant'});return true;}return false;},
  };
})();
