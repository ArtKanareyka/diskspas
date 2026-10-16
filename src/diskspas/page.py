"""Single-page web UI (vanilla JS, no external resources)."""

PAGE = r"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ДискСпас</title>
<link rel="icon" href="data:,">
<style>
:root{--bg1:#f1f3ff;--bg2:#ffffff;--card:#ffffff;--fg:#1b1f3a;--mut:#6b7190;--line:#e3e6f5;--tile:#f6f7ff;
--acc:#4f6df5;--acc2:#8b5cf6;--ok:#16a34a;--bad:#dc2626;--warn:#d97706;--shadow:0 8px 28px rgba(60,70,140,.10)}
@media (prefers-color-scheme:dark){:root{--bg1:#0d1020;--bg2:#161a2e;--card:#1b2038;--fg:#e9ebff;--mut:#9aa1c7;
--line:#2a3050;--tile:#222846;--ok:#4ade80;--bad:#f87171;--warn:#fbbf24;--shadow:0 8px 28px rgba(0,0,0,.35)}}
*{box-sizing:border-box}
[hidden]{display:none!important}
body{margin:0;min-height:100vh;color:var(--fg);background:linear-gradient(160deg,var(--bg1),var(--bg2)) fixed;
font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{max-width:980px;margin:0 auto;padding:22px 20px 4px;display:flex;align-items:center;gap:14px}
.brand{display:flex;align-items:center;gap:14px;flex:1;min-width:0}
.brand svg{width:54px;height:54px;flex:none;filter:drop-shadow(0 6px 14px rgba(79,109,245,.4))}
.brand h1{margin:0;font-size:28px;font-weight:800;letter-spacing:-.6px;line-height:1.1;
background:linear-gradient(90deg,var(--acc),var(--acc2));-webkit-background-clip:text;background-clip:text;color:transparent}
.brand p{margin:2px 0 0;color:var(--mut);font-size:13px}
nav{max-width:980px;margin:0 auto;padding:16px 20px 2px;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.st{display:flex;align-items:center;gap:8px;color:var(--mut);font-size:13px;font-weight:600}
.st i{width:28px;height:28px;border-radius:50%;display:grid;place-items:center;font-style:normal;font-size:13px;
background:var(--card);border:2px solid var(--line)}
.st.on{color:var(--fg)}
.st.on i{border-color:transparent;color:#fff;background:linear-gradient(135deg,var(--acc),var(--acc2));box-shadow:0 4px 12px rgba(79,109,245,.45)}
.st.done i{border-color:transparent;background:var(--ok);color:#fff}
.sep{width:24px;height:2px;background:var(--line);border-radius:2px}
main{max-width:980px;margin:0 auto;padding:4px 20px 56px}
.card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:22px 24px;margin:14px 0;box-shadow:var(--shadow)}
.hero{text-align:center;padding:14px 0 0}
.hero svg{width:104px;height:104px;filter:drop-shadow(0 12px 26px rgba(79,109,245,.45))}
.hero h2{font-size:30px;margin:12px 0 6px;letter-spacing:-.6px}
.hero p{color:var(--mut);margin:0 auto;max-width:540px}
h2{margin:0 0 6px;font-size:21px}h3{margin:18px 0 8px;font-size:15px}
p{margin:6px 0}.mut{color:var(--mut)}.ok{color:var(--ok)}.bad{color:var(--bad)}.warn{color:var(--warn)}
button{font:inherit;font-weight:600;padding:10px 20px;border-radius:12px;border:0;color:#fff;cursor:pointer;
background:linear-gradient(135deg,var(--acc),var(--acc2));box-shadow:0 4px 14px rgba(79,109,245,.35);
transition:transform .08s,box-shadow .15s}
button:hover{transform:translateY(-1px);box-shadow:0 8px 20px rgba(79,109,245,.42)}
button:active{transform:none}
button:disabled{opacity:.45;box-shadow:none;transform:none;cursor:default}
button.ghost{background:transparent;color:var(--fg);box-shadow:none;border:1px solid var(--line)}
button.ghost:hover{background:var(--tile);box-shadow:none}
button.danger{background:var(--bad);box-shadow:none}
a.btn{font-weight:600;padding:10px 18px;border-radius:12px;text-decoration:none;color:var(--fg);border:1px solid var(--line);white-space:nowrap}
a.btn:hover{background:var(--tile)}
input[type=text],input[type=password],input[type=number]{font:inherit;padding:10px 12px;border-radius:12px;
border:1px solid var(--line);background:var(--tile);color:var(--fg);width:100%;outline:0}
input:focus{border-color:var(--acc);box-shadow:0 0 0 3px rgba(79,109,245,.2)}
input[type=checkbox],input[type=radio]{accent-color:var(--acc)}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.row>input{flex:1;min-width:200px}
.acts{display:flex;gap:10px;margin-top:18px;flex-wrap:wrap}
.list{border:1px solid var(--line);border-radius:12px;max-height:340px;overflow:auto;background:var(--tile)}
.li{display:flex;gap:8px;align-items:center;padding:8px 12px;border-bottom:1px solid var(--line);cursor:pointer}
.li:last-child{border-bottom:0}.li:hover{background:var(--card)}
.tree .nd{display:flex;gap:6px;align-items:center;padding:4px 8px;white-space:nowrap;border-radius:8px}
.tree .nd:hover{background:var(--card)}
.tree .tg{width:16px;cursor:pointer;color:var(--mut);user-select:none;text-align:center}
.tree .kids{margin-left:22px}.tree .sz{margin-left:auto;color:var(--mut);font-size:12px;padding-left:12px}
.tree .nm{overflow:hidden;text-overflow:ellipsis}
.chip{display:inline-block;padding:4px 12px;border-radius:999px;border:1px solid var(--line);background:var(--tile);
margin:2px 6px 2px 0;cursor:pointer;font-size:13px}
.chip:hover{border-color:var(--acc);color:var(--acc)}
.k{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:14px 0}
.k div{background:var(--tile);border:1px solid var(--line);border-radius:12px;padding:8px 12px}
.k b{display:block;font-size:18px;margin-top:1px}.k span{font-size:12px;color:var(--mut)}
progress{-webkit-appearance:none;appearance:none;width:100%;height:14px;border:0;border-radius:999px;overflow:hidden;background:var(--line)}
progress::-webkit-progress-bar{background:var(--line);border-radius:999px}
progress::-webkit-progress-value{background:linear-gradient(90deg,var(--acc),var(--acc2));border-radius:999px;transition:width .6s}
progress::-moz-progress-bar{background:linear-gradient(90deg,var(--acc),var(--acc2));border-radius:999px}
td progress{height:8px}
table{border-collapse:collapse;width:100%;font-size:13px}td,th{padding:5px 8px;text-align:left;border-bottom:1px solid var(--line)}
th{color:var(--mut);font-weight:600}.n{text-align:right;white-space:nowrap}.p{word-break:break-all}
details{margin:12px 0}summary{cursor:pointer;color:var(--acc);font-weight:600}
ol,ul.trust{padding-left:22px}li{margin:6px 0}
code{background:var(--tile);padding:2px 7px;border-radius:6px;font-size:13px}
.sw{width:18px;height:18px}
</style></head><body>
<header><div class="brand"><span id="logo"></span><div><h1>ДискСпас</h1><p>Спасаем файлы с Яндекс Диска</p></div></div>
<a class="btn ghost" id="help" target="_blank" rel="noopener" hidden></a></header>
<nav id="steps"></nav>
<main id="main"></main>
<script>
"use strict";
const T = {app:"ДискСпас",trust_h:"Это безопасно? Что происходит с вашими данными",trust_1:"Программа работает только на вашем компьютере. У неё нет своих серверов, поэтому она не может отправить куда-то ваши файлы, токен или статистику: их просто некуда отправлять.",trust_2:"Пароль от Яндекса не нужен, и программа его никогда не просит. Вместо пароля Яндекс выдаёт токен: отдельный ключ, который разрешает только читать файлы. Изменить или удалить что-то на Диске с ним нельзя.",trust_3:"Токен хранится только у вас на компьютере и отправляется только Яндексу. Кнопка «Выйти из аккаунта» удаляет его, а доступ можно отозвать на странице id.yandex.ru/security/access.",trust_4:"Скачанные файлы лежат в выбранной вами папке, и больше их никто не видит. В программе нет рекламы, аналитики и скрытых соединений.",trust_how:"Как это проверить самому",trust_c1:"Окно открывается по адресу 127.0.0.1: это ваш собственный компьютер, а не сайт в интернете.",trust_c2:"Откройте «Монитор ресурсов» (Windows) на вкладке «Сеть»: программа обращается только к серверам Яндекса (cloud-api.yandex.net и storage.yandex.net).",trust_c3:"На странице Яндекса, где вы нажимаете «Разрешить», должно быть написано только «Чтение всего Диска». Если там есть запись или удаление, не разрешайте.",trust_c4:"Токен можно в любой момент отозвать. После этого программа теряет доступ, и ничего больше сделать с вашим Диском не сможет.",details:"Подробности",t_files:"Файлов готово",help:"Помощь и вопросы",lost:"Связь с программой потеряна: скорее всего, она закрылась. Запустите ДискСпас снова и обновите страницу.",hero_h:"Спасаем файлы с Яндекс Диска",hero_p:"Если Диск глючит и файлы не скачиваются, ДискСпас вытащит их на ваш компьютер: сам повторит неудачные попытки и подберёт скорость.",s1:"1. Вход",s2:"2. Что скачать",s3:"3. Куда",s4:"4. Проверка",s5:"5. Загрузка",

nokey:"Страница открыта без ключа доступа. Запустите программу заново и откройте адрес, который она покажет.",
login_h:"Вход в Яндекс Диск",login_lead:"Программа только читает ваши файлы и сохраняет копии на компьютер. В облаке она ничего не меняет и не удаляет.",
token:"Токен доступа",token_ph:"Вставьте сюда токен",login_btn:"Войти",logged_as:"Вы вошли в аккаунт. На Диске занято {0} из {1}.",
cont:"Продолжить",logout:"Выйти из аккаунта",howto:"Где взять токен?",
how_ready1:"Нажмите кнопку ниже: откроется страница Яндекса.",how_ready_btn:"Открыть страницу Яндекса",how_ready2:"Войдите в аккаунт и нажмите «Разрешить». Яндекс покажет длинный токен.",how_ready3:"Скопируйте его и вставьте в поле выше.",
how_new_intro:"Один раз нужно создать своё приложение (это займёт пару минут), чтобы Яндекс выдал токен только для чтения:",
how_new1:"Откройте страницу создания приложения и войдите в Яндекс.",how_new_open:"Открыть страницу создания",
how_new2:"Название — любое, иконка — любая картинка до 1 МБ, почта — ваша.",
how_new3:"Платформа — «Веб-сервисы», Redirect URI: ",
how_new4:"В разделе «Дополнительные» введите cloud_api:disk.read и выберите «Чтение всего Диска». Права на запись не добавляйте.",
how_new5:"Создайте приложение, скопируйте ClientID и вставьте сюда:",client_id:"ClientID",how_new_btn:"Открыть страницу разрешения",
how_new6:"Нажмите «Разрешить», скопируйте показанный токен и вставьте его в поле выше.",
what_h:"Что скачать",what_all:"Весь Диск",what_sel:"Выбрать папки и файлы",what_tip:"Отметьте галочками нужные папки и файлы. Чтобы открыть папку, нажмите на стрелку.",
skipjunk:"Не скачивать служебные и временные файлы (кэш программ, папки AppData, временные файлы Word и т. п.)",order_note:"Порядок такой: сначала фото, видео и документы, потом всё остальное, а служебные и временные файлы — в самом конце.",
selected:"Выбрано: {0}",nothing_sel:"Ничего не выбрано",back:"Назад",next:"Далее",
where_h:"Куда сохранить",where_lead:"Выберите папку на компьютере. Папки с Диска сохранятся внутри неё в том же виде.",
quick:"Быстрый переход",drives:"Диски",up:"Наверх",roots:"Все диски",newfolder:"Создать папку",create:"Создать",folder_name:"Имя новой папки",
path:"Путь",go:"Перейти",choose:"Выбрать эту папку",dest_is:"Папка назначения",free:"свободно {0}",not_chosen:"не выбрана",
review_h:"Всё готово к запуску?",scanning:"Сканирую Диск… Найдено файлов: {0}",scan_err:"Не удалось просканировать Диск: {0}",retry:"Попробовать снова",
sum_files:"Файлов",sum_size:"Общий размер",sum_free:"Свободно на диске",sum_have:"Уже скачано",sum_need:"Осталось скачать",sum_dest:"Куда",junk_info:"Из них служебных и временных: {0} шт. ({1})",junk_skipped:"Служебные и временные файлы пропущены: {0} шт. ({1}).",
no_space:"Не хватает места: нужно {0}, свободно {1}. Выберите другую папку или освободите место.",
start:"Начать скачивание",
prog_h:"Загрузка",ph_listing:"подготовка",ph_downloading:"идёт загрузка",ph_done:"готово",ph_stopped:"остановлено",ph_error:"ошибка",ph_starting:"запуск",ph_unfinished:"почти готово, часть файлов ждёт",
paused:"на паузе",pause:"Пауза",resume:"Продолжить",stop:"Остановить",stop2:"Точно остановить?",
t_progress:"Прогресс",t_done:"Скачано / всего",t_left:"Осталось",t_speed:"Скорость (10 с)",t_speed60:"Скорость (60 с)",t_avg:"Средняя",t_eta:"Осталось времени",t_elapsed:"Прошло",
t_ok:"Скачано файлов",t_skip:"Уже были скачаны",t_queue:"В очереди",t_active:"Активных / лимит",t_wait:"Ждут повтора",t_fail:"Не скачались",t_err:"Сбоев сети",t_auto:"Автонастройка",
active:"Скачиваются сейчас",recent:"Недавно завершены",errors:"Последние сбои",waiting:"Ждут следующего круга (сервер Яндекса пока не отдаёт эти файлы)",failed:"Не удалось",none:"нет",
c_file:"Файл",c_size:"Размер",c_prog:"Прогресс",c_age:"Время",c_retry:"Повторы",
wait_expl:"Это не ошибка программы: часть серверов Яндекса сейчас не отдаёт файлы. Программа сама повторит попытку позже.",
fin_done:"Готово! Все файлы скачаны.",fin_stopped:"Остановлено. Прогресс сохранён: чтобы продолжить, начните заново с той же папкой сохранения.",fin_unf:"Почти готово: {0} файлов Яндекс пока не отдаёт. Запустите программу позже с той же папкой — она докачает остальное.",
fin_report:"Подробный отчёт: {0}",open_folder:"Открыть папку",new_dl:"Новая загрузка",safety:"Не удаляйте файлы из облака, пока не убедились, что копия в порядке. Когда закончите, отзовите доступ программы: id.yandex.ru/security/access",
e_not_logged_in:"Нужно войти.",e_bad_link:"Это не похоже на ссылку Яндекс Диска. Она должна начинаться с https://disk.yandex.ru/ или https://yadi.sk/",e_link_gone:"По этой ссылке ничего нет: она удалена или закрыта владельцем.",e_link_failed:"Не удалось открыть ссылку. Проверьте интернет и попробуйте ещё раз.",
link_h:"У меня есть ссылка на файлы",link_lead:"Вам прислали ссылку вида disk.yandex.ru/d/… ? Вставьте её сюда — токен и вход не нужны.",link_ph:"https://disk.yandex.ru/d/…",link_btn:"Открыть ссылку",or_own:"Или войдите в свой аккаунт, чтобы скачать собственный Диск:",linked_as:"Ссылка открыта: {0}",e_bad_token:"Яндекс не принял этот токен. Проверьте, что скопировали его целиком.",e_empty_token:"Вставьте токен.",
e_no_space:"На диске не хватает места.",e_denied:"Нет доступа к этой папке.",e_bad_name:"Недопустимое имя папки.",e_busy:"Сначала остановите текущую загрузку.",e_no_dest:"Выберите папку для сохранения.",e_root_dest:"Выберите папку, а не весь диск целиком. Можно создать новую папку кнопкой ниже.",e_forbidden:"Нет доступа. Откройте программу заново.",
loading:"Загрузка…",empty_dir:"(вложенных папок нет)",folder:"папка"};
function t(k,...a){let s=T[k]||k;a.forEach((v,i)=>{s=s.replace("{"+i+"}",v)});return s}
function errText(e){return (e&&e.code&&T["e_"+e.code])||(e&&e.message)||String(e)}

const KEY=(()=>{try{const m=location.hash.match(/k=([^&]+)/);if(m){sessionStorage.k=m[1];history.replaceState(null,"",location.pathname)}return sessionStorage.k||""}catch(e){return ""}})();
async function api(path,body){
  const r=await fetch(path,{method:body===undefined?"GET":"POST",headers:{"X-Key":KEY,"Content-Type":"application/json"},body:body===undefined?undefined:JSON.stringify(body)});
  let j={};try{j=await r.json()}catch(e){}
  if(!r.ok){const e=new Error(j.error||r.statusText);e.code=j.code;e.status=r.status;throw e}
  return j}

function h(tag,props,...kids){const e=document.createElement(tag);
  for(const k in (props||{})){const v=props[k];
    if(k==="class")e.className=v;else if(k.startsWith("on"))e.addEventListener(k.slice(2),v);
    else if(k==="value")e.value=v;else if(v===true)e.setAttribute(k,"");else if(v!==false&&v!=null)e.setAttribute(k,v)}
  kids.flat().forEach(c=>{if(c==null||c===false)return;e.appendChild(typeof c==="string"||typeof c==="number"?document.createTextNode(String(c)):c)});return e}
const $=id=>document.getElementById(id);
const sz=b=>b==null?"-":b>=2**30?(b/2**30).toFixed(2)+" ГБ":b>=2**20?(b/2**20).toFixed(1)+" МБ":b>=1024?(b/1024).toFixed(0)+" КБ":b+" Б";
const dur=s=>{if(s==null||!isFinite(s))return "-";s=Math.round(s);const d=Math.floor(s/86400),hh=Math.floor(s%86400/3600),m=Math.floor(s%3600/60);return (d?d+" д ":"")+(hh?hh+" ч ":"")+m+" мин"+(s<3600?" "+(s%60)+" с":"")};
const rel=p=>p.replace(/^disk:/,"")||"/";

const S={step:1,st:null,mode:"all",selection:new Set(),skipJunk:false,dest:"",browse:null,maxThr:128,verify:true,scanSig:"",booted:false,confirm:{}};
const STEPS=["s1","s2","s3","s4","s5"];

const LOGO='<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#4f6df5"/><stop offset="1" stop-color="#8b5cf6"/></linearGradient></defs><rect width="64" height="64" rx="15" fill="url(#lg)"/><circle cx="32" cy="32" r="15" fill="none" stroke="#fff" stroke-width="11"/><circle cx="32" cy="32" r="15" fill="none" stroke="#ff7a45" stroke-width="11" stroke-dasharray="11.78 11.78" transform="rotate(-22.5 32 32)"/></svg>';
function hero(){const d=h("div",{class:"hero"});d.innerHTML=LOGO.replace('id="lg"','id="lg2"').replace('url(#lg)','url(#lg2)');
  d.appendChild(h("h2",null,t("hero_h")));d.appendChild(h("p",null,t("hero_p")));return d}
function renderSteps(){const n=$("steps");n.textContent="";STEPS.forEach((k,i)=>{
  if(i)n.appendChild(h("span",{class:"sep"}));
  const cls="st"+(S.step===i+1?" on":(S.step>i+1?" done":""));
  n.appendChild(h("span",{class:cls},h("i",null,S.step>i+1?"\u2713":String(i+1)),t(k).replace(/^\d+\.\s*/,"")))})}
function show(step){S.step=step;renderSteps();const m=$("main");m.textContent="";if(step===1)m.appendChild(hero());
  ({1:scrLogin,2:scrWhat,3:scrWhere,4:scrReview,5:scrProgress})[step](m)}

function trustCard(){
  return h("div",{class:"card"},h("h3",{style:"margin-top:0"},"\u{1F512} "+t("trust_h")),
    h("ul",{class:"trust"},["trust_1","trust_2","trust_3","trust_4"].map(k=>h("li",null,t(k)))),
    h("details",null,h("summary",null,t("trust_how")),
      h("ul",{class:"trust"},["trust_c1","trust_c2","trust_c3","trust_c4"].map(k=>h("li",null,t(k))))))}
/* ---------- step 1: login ---------- */
function scrLogin(m){
  const st=S.st;
  if(st&&st.logged_in){
    m.appendChild(h("div",{class:"card"},h("h2",null,t("login_h")),
      h("p",{class:"ok"},st.public?t("linked_as",st.public.name):t("logged_as",sz(st.disk.used),sz(st.disk.total))),
      h("div",{class:"acts"},h("button",{onclick:()=>show(S.st.job?5:2)},t("cont")),
        h("button",{class:"ghost",onclick:async()=>{try{await api("/api/logout",{});await refresh();show(1)}catch(e){alert(errText(e))}}},t("logout")))));
    return}
  const err=h("p",{class:"bad",id:"lerr"});
  const tok=h("input",{type:"password",id:"tok",placeholder:t("token_ph"),autocomplete:"off"});
  const cid=h("input",{type:"text",id:"cid",value:(st&&st.client_id)||"",placeholder:t("client_id")});
  const go=async()=>{err.textContent="";try{await api("/api/login",{token:tok.value,client_id:cid.value||undefined});tok.value="";await refresh();show(2)}catch(e){err.textContent=errText(e)}};
  tok.addEventListener("keydown",e=>{if(e.key==="Enter")go()});
  let how;
  if(st&&st.client_id_set){
    how=h("ol",null,h("li",null,t("how_ready1")," ",h("button",{class:"ghost",onclick:()=>window.open(st.authorize_url,"_blank","noopener")},t("how_ready_btn"))),
      h("li",null,t("how_ready2")),h("li",null,t("how_ready3")));
  }else{
    how=h("div",null,h("p",null,t("how_new_intro")),h("ol",null,
      h("li",null,t("how_new1")," ",h("button",{class:"ghost",onclick:()=>window.open("https://oauth.yandex.ru/client/new","_blank","noopener")},t("how_new_open"))),
      h("li",null,t("how_new2")),
      h("li",null,t("how_new3"),h("code",null,"https://oauth.yandex.ru/verification_code")),
      h("li",null,t("how_new4")),
      h("li",null,t("how_new5"),h("div",{class:"row",style:"margin-top:6px"},cid,
        h("button",{class:"ghost",onclick:()=>{const v=cid.value.trim();if(v)window.open("https://oauth.yandex.ru/authorize?response_type=token&client_id="+encodeURIComponent(v),"_blank","noopener")}},t("how_new_btn")))),
      h("li",null,t("how_new6"))))}
  const lerr=h("p",{class:"bad"});
  const lnk=h("input",{type:"text",placeholder:t("link_ph"),autocomplete:"off"});
  const golink=async()=>{lerr.textContent="";try{await api("/api/login_public",{link:lnk.value});await refresh();show(2)}catch(e){lerr.textContent=errText(e)}};
  lnk.addEventListener("keydown",e=>{if(e.key==="Enter")golink()});
  m.appendChild(h("div",{class:"card"},h("h2",null,t("link_h")),h("p",{class:"mut"},t("link_lead")),
    h("div",{class:"row"},lnk,h("button",{onclick:golink},t("link_btn"))),lerr));
  m.appendChild(h("div",{class:"card"},h("h2",null,t("login_h")),h("p",{class:"mut"},t("login_lead")),
    h("h3",null,t("token")),h("div",{class:"row"},tok,h("button",{onclick:go},t("login_btn"))),err,
    h("details",{open:true},h("summary",null,t("howto")),how)));
  m.appendChild(trustCard());
  tok.focus()}

/* ---------- step 2: what to download ---------- */
function updSel(){const n=$("selinfo");if(!n)return;n.textContent=S.mode==="all"?"":(S.selection.size?t("selected",S.selection.size):t("nothing_sel"));
  const nx=$("next2");if(nx)nx.disabled=(S.mode==="select"&&!S.selection.size)}
function setKids(box,on){box.querySelectorAll("input[type=checkbox]").forEach(c=>{c.checked=on;c.disabled=on})}
async function loadKids(path,box,inherit){
  box.textContent=t("loading");
  let items;try{items=await api("/api/tree?path="+encodeURIComponent(path))}catch(e){box.textContent=errText(e);return}
  box.textContent="";
  items.forEach(it=>{
    const isDir=it.type==="dir",kids=h("div",{class:"kids",hidden:true});let opened=false;
    const cb=h("input",{type:"checkbox",class:"sw",checked:inherit||S.selection.has(it.path),disabled:inherit,
      onchange:e=>{if(cb.checked){[...S.selection].forEach(p=>{if(p.startsWith(it.path+"/"))S.selection.delete(p)});S.selection.add(it.path)}else S.selection.delete(it.path);
        if(isDir)setKids(kids,cb.checked);updSel()}});
    const tg=h("span",{class:"tg",onclick:async()=>{if(!isDir)return;if(!opened){opened=true;kids.hidden=false;tg.textContent="▾";await loadKids(it.path,kids,cb.checked)}else{kids.hidden=!kids.hidden;tg.textContent=kids.hidden?"▸":"▾"}}},isDir?"▸":"");
    box.appendChild(h("div",{class:"nd"},tg,cb,h("span",null,isDir?"📁":"📄"),h("span",{class:"nm",title:it.name},it.name),h("span",{class:"sz"},isDir?"":sz(it.size))));
    box.appendChild(kids)})
  if(!items.length)box.textContent=t("empty_dir")}
function scrWhat(m){
  const tree=h("div",{class:"list tree",id:"tree",hidden:S.mode==="all"});
  const setMode=v=>{S.mode=v;tree.hidden=v==="all";$("tip").hidden=v==="all";if(v==="select"&&!tree.dataset.loaded){tree.dataset.loaded=1;loadKids("disk:/",tree,false)}updSel()};
  m.appendChild(h("div",{class:"card"},h("h2",null,t("what_h")),
    h("p",null,h("label",null,h("input",{type:"radio",name:"mode",checked:S.mode==="all",onchange:()=>setMode("all")})," ",t("what_all"))),
    h("p",null,h("label",null,h("input",{type:"radio",name:"mode",checked:S.mode==="select",onchange:()=>setMode("select")})," ",t("what_sel"))),
    h("p",{class:"mut",id:"tip",hidden:S.mode==="all"},t("what_tip")),tree,h("p",{class:"mut",id:"selinfo"}),
    h("p",null,h("label",null,h("input",{type:"checkbox",checked:S.skipJunk,onchange:e=>{S.skipJunk=e.target.checked}})," ",t("skipjunk"))),
    h("p",{class:"mut"},t("order_note")),
    h("div",{class:"acts"},h("button",{class:"ghost",onclick:()=>show(1)},t("back")),h("button",{id:"next2",onclick:()=>show(3)},t("next")))));
  if(S.mode==="select"){tree.dataset.loaded=1;loadKids("disk:/",tree,false)}updSel()}

/* ---------- step 3: where ---------- */
async function loadFs(path){
  const box=$("fsbox");if(!box)return;box.textContent=t("loading");let d;
  try{d=await api("/api/fs?path="+encodeURIComponent(path||""))}catch(e){box.textContent=errText(e);return}
  S.browse=d.path;box.textContent="";
  $("fspath").value=d.path;
  const info=$("fsinfo");info.textContent=d.path?(d.free!=null?t("free",sz(d.free)):""):"";
  $("choose").disabled=!d.path;$("mk").hidden=!d.path;
  const q=$("quick");q.textContent="";
  if(d.path===""){
    (d.quick||[]).forEach(x=>q.appendChild(h("span",{class:"chip",onclick:()=>loadFs(x.path)},x.name)));
    (d.roots||[]).forEach(x=>box.appendChild(h("div",{class:"li",onclick:()=>loadFs(x.path)},"💽 ",x.name)));return}
  box.appendChild(h("div",{class:"li",onclick:()=>loadFs(d.parent||"")},"↑ ",d.parent?t("up"):t("roots")));
  d.dirs.forEach(n=>{const sep=d.path.includes("\\")?"\\":"/";const full=d.path.endsWith(sep)?d.path+n:d.path+sep+n;
    box.appendChild(h("div",{class:"li",onclick:()=>loadFs(full)},"📁 ",n))});
  if(!d.dirs.length)box.appendChild(h("div",{class:"li mut"},t("empty_dir")))}
function updDest(){const n=$("destnow");if(!n)return;n.textContent=S.dest||t("not_chosen");n.className=S.dest?"ok":"mut";const nx=$("next3");if(nx)nx.disabled=!S.dest}
function scrWhere(m){
  const nm=h("input",{type:"text",id:"newname",placeholder:t("folder_name")});
  m.appendChild(h("div",{class:"card"},h("h2",null,t("where_h")),h("p",{class:"mut"},t("where_lead")),
    h("p",null,h("b",null,t("dest_is")+": "),h("span",{id:"destnow"})),
    h("div",{class:"row"},h("input",{type:"text",id:"fspath",onkeydown:e=>{if(e.key==="Enter")loadFs(e.target.value)}}),h("button",{class:"ghost",onclick:()=>loadFs($("fspath").value)},t("go"))),
    h("p",{id:"quick",style:"margin:8px 0 4px"}),
    h("div",{class:"list",id:"fsbox",style:"margin-top:6px"}),
    h("p",{class:"mut",id:"fsinfo"}),
    h("div",{class:"row",id:"mk",hidden:true},nm,h("button",{class:"ghost",onclick:async()=>{try{const d=await api("/api/mkdir",{parent:S.browse,name:nm.value});nm.value="";await loadFs(d.path)}catch(e){alert(errText(e))}}},t("newfolder"))),
    h("div",{class:"acts"},h("button",{id:"choose",onclick:()=>{S.dest=S.browse;updDest()}},t("choose")),
      h("button",{class:"ghost",onclick:()=>show(2)},t("back")),h("button",{id:"next3",onclick:()=>show(4)},t("next")))));
  const start=S.dest||(S.st&&S.st.dest)||"";if(S.st&&S.st.dest&&!S.dest)S.dest=S.st.dest;updDest();loadFs(start)}

/* ---------- step 4: review ---------- */
function savePrefs(){api("/api/prefs",{mode:S.mode,selection:[...S.selection],skip_junk:S.skipJunk,verify:S.verify,max_threads:S.maxThr}).catch(()=>{})}
function scanSig(){return JSON.stringify([S.mode,[...S.selection].sort(),S.skipJunk])}
async function scrReview(m){
  S.rvSig="";m.appendChild(h("div",{class:"card",id:"rv"}));
  const st=S.st,sig=scanSig();
  if(!(st.scan.state==="done"&&S.scanSig===sig)&&st.scan.state!=="scanning"){
    S.scanSig=sig;savePrefs();try{await api("/api/scan",{selection:S.mode==="all"?[]:[...S.selection],skip_junk:S.skipJunk})}catch(e){$("rv").textContent=errText(e);return}
    await refresh()}
  renderReview()}
async function renderReview(){
  const box=$("rv");if(!box||S.step!==4)return;const st=S.st,sc=st.scan;
  const rs=[sc.state,sc.count,st.plan&&st.plan.files].join();if(rs===S.rvSig&&box.childNodes.length)return;S.rvSig=rs;box.textContent="";
  box.appendChild(h("h2",null,t("review_h")));
  if(sc.state==="scanning"||sc.state==="idle"){box.appendChild(h("p",null,t("scanning",sc.count)));
    box.appendChild(h("div",{class:"acts"},h("button",{class:"ghost",onclick:()=>show(3)},t("back"))));return}
  if(sc.state==="error"){box.appendChild(h("p",{class:"bad"},t("scan_err",sc.error)));
    box.appendChild(h("div",{class:"acts"},h("button",{class:"ghost",onclick:()=>show(3)},t("back")),h("button",{onclick:()=>{S.scanSig="";show(4)}},t("retry"))));return}
  const p=st.plan;let free=null,need=p.bytes,have=0;
  try{const r=await api("/api/remaining?path="+encodeURIComponent(S.dest));free=r.free;need=r.need;have=r.already}catch(e){}
  const short=free!=null&&need>free;
  box.appendChild(h("div",{class:"k"},
    h("div",null,h("span",null,t("sum_files")),h("b",null,p.files.toLocaleString())),
    h("div",null,h("span",null,t("sum_size")),h("b",null,sz(p.bytes))),
    have>0?h("div",null,h("span",null,t("sum_have")),h("b",null,sz(have))):null,
    have>0?h("div",null,h("span",null,t("sum_need")),h("b",null,sz(need))):null,
    h("div",null,h("span",null,t("sum_free")),h("b",{class:short?"bad":""},sz(free)))));
  box.appendChild(h("p",null,h("b",null,t("sum_dest")+": "),S.dest));
  if(p.skipped_junk)box.appendChild(h("p",{class:"mut"},t("junk_skipped",p.junk_files,sz(p.junk_bytes))));
  else if(p.junk_files)box.appendChild(h("p",{class:"mut"},t("junk_info",p.junk_files,sz(p.junk_bytes))));
  if(short)box.appendChild(h("p",{class:"bad"},t("no_space",sz(need),sz(free))));
  const err=h("p",{class:"bad"});
  box.appendChild(err);
  box.appendChild(h("div",{class:"acts"},h("button",{class:"ghost",onclick:()=>show(3)},t("back")),
    h("button",{disabled:short||!S.dest,onclick:async()=>{err.textContent="";try{savePrefs();await api("/api/start",{dest:S.dest,options:{max_threads:S.maxThr,verify:S.verify}});await refresh();show(5)}catch(e){err.textContent=errText(e)}}},t("start"))))}

/* ---------- step 5: progress ---------- */
function phaseText(j,running){if(j.paused)return t("paused");
  if(running){return j.phase==="downloading"?t("ph_downloading"):(t("ph_"+j.phase)||j.phase)}
  if(j.phase==="stopped"||j.phase==="interrupted")return t("ph_stopped");
  if(j.phase==="error")return t("ph_error");
  return j.phase&&j.phase.indexOf("unfinished")>=0?t("ph_unfinished"):t("ph_done")}
function twoStep(key,label,label2,fn){const b=h("button",{class:"ghost",onclick:()=>{
  if(S.confirm[key]){clearTimeout(S.confirm[key]);S.confirm[key]=0;fn()}
  else{b.textContent=label2;S.confirm[key]=setTimeout(()=>{S.confirm[key]=0;b.textContent=label},3500)}}},label);return b}
function scrProgress(m){
  m.appendChild(h("div",{class:"card"},h("h2",null,t("prog_h")," ",h("span",{class:"mut",id:"pph",style:"font-size:15px"})),
    h("progress",{id:"pbar",max:1,value:0}),h("div",{class:"k",id:"ptiles"}),h("div",{class:"acts",id:"pctl"}),h("div",{id:"pfin"})));
  const det=h("details",{class:"card",id:"pdet"},h("summary",null,t("details")),h("div",{class:"k",id:"ptiles2",style:"margin-top:12px"}));
  m.appendChild(det);
  det.appendChild(h("div",{class:"card"},h("h3",{style:"margin-top:0"},t("active")," ",h("span",{class:"mut",id:"pna"})),h("table",{id:"pact"})));
  det.appendChild(h("div",{class:"card",id:"cwait",hidden:true},h("h3",{style:"margin-top:0"},t("waiting")),h("p",{class:"mut"},t("wait_expl")),h("table",{id:"pdef"})));
  det.appendChild(h("div",{class:"card"},h("h3",{style:"margin-top:0"},t("errors")),h("table",{id:"perr"}),h("h3",null,t("failed")),h("table",{id:"pfail"}),h("h3",null,t("recent")),h("table",{id:"prec"})));
  S.ctlSig="";renderProgress()}
function rows(a,f){return a.length?a.map(f):[h("tr",null,h("td",{class:"mut"},t("none")))]}
function fill(id,kids){const n=$(id);if(!n)return;n.textContent="";kids.flat().forEach(k=>n.appendChild(k))}
function renderProgress(){
  if(S.step!==5)return;const st=S.st,j=st.job;if(!j)return;const running=st.running;
  $("pph").textContent=phaseText(j,running);
  $("pbar").max=j.total_size||1;$("pbar").value=j.done_total||0;
  const filesDone=j.ok+j.skip;
  const K=[[t("t_eta"),running?dur(j.eta):"-"],[t("t_speed"),sz(j.speed10)+"/с"],[t("t_left"),sz(j.remaining)],[t("t_files"),filesDone.toLocaleString()+" / "+j.total_files.toLocaleString()]];
  const K2=[[t("t_progress"),(j.total_size?(100*j.done_total/j.total_size).toFixed(1):"0")+"%"],[t("t_done"),sz(j.done_total)+" / "+sz(j.total_size)],[t("t_speed60"),sz(j.speed60)+"/с"],[t("t_avg"),sz(j.avg)+"/с"],[t("t_elapsed"),dur(j.elapsed)],[t("t_skip"),j.skip.toLocaleString()],[t("t_queue"),j.queued.toLocaleString()],[t("t_active"),j.active.length+" / "+j.limit],[t("t_wait"),j.deferred_count],[t("t_fail"),j.failed],[t("t_err"),j.errors_total],[t("t_auto"),j.note||"-"]];
  fill("ptiles",K.map(x=>h("div",null,h("span",null,x[0]),h("b",null,String(x[1])))));
  fill("ptiles2",K2.map(x=>h("div",null,h("span",null,x[0]),h("b",null,String(x[1])))));
  const sig=[running,j.paused,j.phase].join();
  if(S.ctlSig!==sig){S.ctlSig=sig;const c=$("pctl");c.textContent="";
    if(running){c.appendChild(h("button",{onclick:async()=>{await api(j.paused?"/api/resume":"/api/pause",{});await refresh()}},j.paused?t("resume"):t("pause")));
      c.appendChild(twoStep("stop",t("stop"),t("stop2"),async()=>{await api("/api/stop",{});await refresh()}))}
    const f=$("pfin");f.textContent="";
    if(!running){const un=(j.deferred_count||0);let msg,cls;
      if(j.phase==="stopped"||j.phase==="interrupted"){msg=t("fin_stopped");cls="warn"}
      else if(un>0){msg=t("fin_unf",un);cls="warn"}else{msg=t("fin_done");cls="ok"}
      f.appendChild(h("p",{class:cls,style:"font-weight:600;font-size:17px"},msg));
      f.appendChild(h("p",{class:"mut"},t("fin_report",st.dest+"/.diskspas/report.txt")));
      f.appendChild(h("p",{class:"mut"},t("safety")));
      f.appendChild(h("div",{class:"acts"},h("button",{onclick:()=>api("/api/open",{path:st.dest}).catch(e=>alert(errText(e)))},t("open_folder")),
        h("button",{class:"ghost",onclick:async()=>{await api("/api/reset",{});S.scanSig="";await refresh();show(2)}},t("new_dl"))))}}
  $("pna").textContent="("+j.active.length+")";
  fill("pact",[h("tr",null,h("th",null,t("c_file")),h("th",{class:"n"},t("c_size")),h("th",{style:"width:22%"},t("c_prog")),h("th",{class:"n"},"%"),h("th",{class:"n"},t("c_age")),h("th",{class:"n"},t("c_retry"))),
    ...rows(j.active,r=>h("tr",null,h("td",{class:"p"},rel(r.path)),h("td",{class:"n"},sz(r.size)),h("td",null,h("progress",{max:r.size,value:r.done})),h("td",{class:"n"},(100*r.done/r.size).toFixed(0)),h("td",{class:"n"},dur(r.age)),h("td",{class:"n"},r.tries)))]);
  $("cwait").hidden=!(j.deferred&&j.deferred.length);
  fill("pdef",rows(j.deferred,d=>h("tr",null,h("td",{class:"p"},rel(d.path)),h("td",{class:"n"},sz(d.size)))));
  fill("perr",rows(j.errors,e=>h("tr",null,h("td",{class:"mut",style:"width:70px"},e.t),h("td",{class:"bad"},e.msg))));
  fill("pfail",rows(j.failed_list,d=>h("tr",null,h("td",{class:"p"},rel(d.path)),h("td",{class:"bad"},d.why))));
  fill("prec",rows(j.recent,r=>h("tr",null,h("td",{class:"mut",style:"width:70px"},r.t),h("td",{class:"p"},rel(r.path)),h("td",{class:"n"},sz(r.size)),h("td",{class:"n"},dur(r.secs)))))}

/* ---------- boot / poll ---------- */
async function refresh(){S.st=await api("/api/status")}
async function tick(){
  try{await refresh();S.fails=0}catch(e){if(e.status===403){$("main").textContent=t("nokey")}else if(!e.status&&++S.fails>=3){$("main").textContent=t("lost");clearInterval(S.timer)}return}
  const hb=$("help");if(S.st.support_url){hb.hidden=false;hb.href=S.st.support_url;hb.textContent=t("help")}else hb.hidden=true;
  if(!S.booted){S.booted=true;
    if(S.st.dest)S.dest=S.dest||S.st.dest;
    const pf=S.st.prefs;if(pf){S.mode=pf.mode==="select"?"select":"all";S.selection=new Set(pf.selection||[]);S.skipJunk=!!pf.skip_junk;S.verify=pf.verify!==false;S.maxThr=pf.max_threads||128}
    show(!S.st.logged_in?1:(S.st.job?5:2));return}
  if(S.step===4)renderReview();else if(S.step===5)renderProgress();
  else if(S.step!==1&&!S.st.logged_in)show(1)}
$("logo").innerHTML=LOGO;document.querySelector("link[rel=icon]").href="data:image/svg+xml,"+encodeURIComponent(LOGO);
renderSteps();
if(!KEY){$("main").textContent=t("nokey")}else{tick();S.timer=setInterval(tick,1000)}
</script></body></html>
"""
