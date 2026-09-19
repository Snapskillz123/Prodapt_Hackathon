import {test,expect} from '@playwright/test';
import {plan} from './fixtures.js';

test('register, chat, display plan, budget, packing, download and delete account',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');
 await page.getByLabel('Your name').fill('Explorer');
 await page.getByLabel('Email address').fill(`ui-${Date.now()}@example.com`);
 await page.getByLabel('Password',{exact:true}).fill('test-password-for-roam');
 await page.getByRole('button',{name:'Let’s explore'}).click();
 await expect(page.getByRole('heading',{name:/Where to next/})).toBeVisible();
 await page.screenshot({path:'artifacts/welcome-desktop.png',fullPage:true});
 // UI test isolates provider nondeterminism. Backend + real graph are tested separately.
 await page.route('**/api/chats/*/messages',async route=>{
   const req=route.request().postDataJSON();
   const id=route.request().url().split('/').at(-2);
   await route.fulfill({json:{id,title:'Trip to Jaipur',profile:plan.profile,plan,version:1,messages:[{role:'user',content:req.message},{role:'assistant',content:plan.summary}]}});
 });
 await page.getByRole('textbox',{name:'Message Roam'}).fill('Plan a relaxed trip to Jaipur');
 await page.getByRole('button',{name:'Send message',exact:true}).click();
 await expect(page.locator('.plan-panel')).toBeVisible();
 await expect(page.locator('.activity')).toHaveCount(plan.days.reduce((n,d)=>n+d.activities.length,0));
 await page.screenshot({path:'artifacts/itinerary-desktop.png',fullPage:true});
 await page.getByRole('tab',{name:'budget',exact:true}).click();
 await expect(page.getByText('ESTIMATED GROUP TOTAL')).toBeVisible();
 await page.getByRole('tab',{name:'packing',exact:true}).click();
 await page.locator('.packing-item input').first().check();
 await expect(page.locator('.packing-item input').first()).toBeChecked();
 const downloadPromise=page.waitForEvent('download');
 await page.getByRole('button',{name:'Download itinerary'}).click();
 expect((await downloadPromise).suggestedFilename()).toBe('roam-itinerary.json');
 await page.setViewportSize({width:390,height:844});
 await expect(page.getByRole('button',{name:'Open navigation'})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await page.screenshot({path:'artifacts/chat-mobile.png',fullPage:true});
 await page.getByRole('button',{name:'Open navigation'}).click();
 page.once('dialog',dialog=>dialog.accept());
 await page.getByRole('button',{name:'Delete my account & data'}).click();
 await expect(page.getByRole('heading',{name:'A world of possibilities.'})).toBeVisible();
 expect(errors).toEqual([]);
});
