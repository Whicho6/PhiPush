let config={API_BASE_URL:'http://127.0.0.1:8000'};try{config=require('../config.js')}catch(e){}
function request(path,method='GET',data){const app=getApp();return new Promise((resolve,reject)=>wx.request({url:config.API_BASE_URL+path,method,data,header:{'Content-Type':'application/json',...(app.globalData.sessionId?{'X-PhiPush-Session':app.globalData.sessionId}:{})},success:r=>r.statusCode>=200&&r.statusCode<300?resolve(r.data):reject(new Error(r.data.detail||'请求失败')),fail:reject}))}
module.exports={request,base:config.API_BASE_URL}
