import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import * as XLSX from "xlsx";
import { readFileSync } from "node:fs";
import path from "node:path";
import { seed, cleanup, createProduct, createSupplier, SeedContext } from "../../../testing/seed";
import { startTestServer, TestServer, postJson, jsonHeaders, loginAndGetToken } from "../../../testing/helpers";
let ctx: SeedContext, server: TestServer;
let admin: string, tienda: string, inventario: string, supplierId: number;
before(async()=>{ctx=await seed("segunda");server=await startTestServer();supplierId=await createSupplier(ctx);[admin,tienda,inventario]=await Promise.all(["admin","tienda","inventario"].map(async role=>{const u=ctx.users[role as keyof typeof ctx.users];return loginAndGetToken(server.baseUrl,u.email,u.password);}));});
after(async()=>{await cleanup(ctx);await server.close();});
const stock=async(productId:number,locationId:number)=>(await ctx.prisma.inventory.findUniqueOrThrow({where:{productId_locationId:{productId,locationId}}})).stock;
function invoiceBytes(rows:unknown[]){const b=XLSX.utils.book_new();XLSX.utils.book_append_sheet(b,XLSX.utils.json_to_sheet(rows),"Factura");return XLSX.write(b,{type:"buffer",bookType:"xlsx"});}
function upload(bytes:Buffer,rate="7"){const form=new FormData();form.append("file",new Blob([bytes],{type:"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}),"factura.xlsx");form.append("supplierId",String(supplierId));form.append("exchangeRate",rate);form.append("locationId",String(ctx.locationIds.almacen));return fetch(`${server.baseUrl}/api/costs/import-invoice`,{method:"POST",headers:{authorization:`Bearer ${admin}`},body:form});}

test("factura idéntica concurrente registra costo y stock solo una vez, y detecta parámetros cambiados",async()=>{
 const p=await createProduct(ctx,{stockAlmacen:1});const bytes=invoiceBytes([{Codigo:p.itemCode,Cantidad:2,Precio:5}]);
 const responses=await Promise.all([upload(bytes),upload(bytes)]);
 for(const r of responses)assert.equal(r.status,200,await r.clone().text());
 const bodies=await Promise.all(responses.map(r=>r.json())) as any[];
 assert.deepEqual(bodies.map(b=>b.replayed).sort(),[false,true]);
 assert.equal(await stock(p.id,ctx.locationIds.almacen),3);
 assert.equal(await ctx.prisma.cost.count({where:{productId:p.id}}),1);
 assert.equal((await upload(bytes,"6")).status,409);
 assert.equal(await stock(p.id,ctx.locationIds.almacen),3);
});
test("una fila inválida revierte la factura completa, sin bloquear una corrección posterior",async()=>{
 const p=await createProduct(ctx,{stockAlmacen:1});
 const res=await upload(invoiceBytes([{Codigo:p.itemCode,Cantidad:2,Precio:5},{Codigo:"NO-EXISTE-SEGUNDA",Cantidad:1,Precio:5}]));
 assert.equal(res.status,400,await res.clone().text());
 assert.equal(await stock(p.id,ctx.locationIds.almacen),1);
 assert.equal(await ctx.prisma.cost.count({where:{productId:p.id}}),0);
});
test("reintento concurrente de movimiento conserva identidad, cantidades y auditoría",async()=>{
 const p=await createProduct(ctx,{stockAlmacen:10,stockTienda:0});
 const payload={operationId:crypto.randomUUID(),productId:p.id,fromLocationId:ctx.locationIds.almacen,toLocationId:ctx.locationIds.tienda,quantity:4};
 const responses=await Promise.all([postJson(server.baseUrl,"/api/movements",payload,inventario),postJson(server.baseUrl,"/api/movements",payload,inventario)]);
 for(const r of responses)assert.equal(r.status,201,await r.clone().text());
 const ids=(await Promise.all(responses.map(r=>r.json())) as any[]).map(m=>m.id);assert.equal(ids[0],ids[1]);
 assert.equal(await stock(p.id,ctx.locationIds.almacen),6);assert.equal(await stock(p.id,ctx.locationIds.tienda),4);
 assert.equal(await ctx.prisma.movement.count({where:{productId:p.id}}),1);
 assert.equal((await postJson(server.baseUrl,"/api/movements",{...payload,quantity:2},inventario)).status,400);
});
test("legacy price2 no cambia POR MENOR ni bloquea un POR MAYOR válido",async()=>{
 const p=await createProduct(ctx,{price1:100,price2:1,wholesalePrice:80,stockTienda:8});
 for(const [priceMode,price] of [["POR_MENOR",100],["POR_MAYOR",80]] as const){
  const response=await postJson(server.baseUrl,"/api/sales",{items:[{productId:p.id,quantity:1,priceMode,unitPrice:0.01}],payments:[{method:"QR",amount:price}]},tienda);
  assert.equal(response.status,201,await response.clone().text());assert.equal((await response.json() as any).items[0].unitPrice,price);
 }
 assert.equal((await postJson(server.baseUrl,"/api/sales",{items:[{productId:p.id,quantity:1,priceTier:"PRICE2"}],payments:[{method:"QR",amount:1}]},tienda)).status,400);
});
test("detalles de venta y devolución de TIENDA no exponen costo",async()=>{
 const p=await createProduct(ctx,{stockTienda:2});const sale=await(await postJson(server.baseUrl,"/api/sales",{items:[{productId:p.id,quantity:1}],payments:[{method:"QR",amount:100}]},tienda)).json() as any;
 for(const url of [`/api/sales/${sale.id}`,`/api/returns/sale/${sale.id}`]){const r=await fetch(server.baseUrl+url,{headers:jsonHeaders(tienda)});assert.equal(r.status,200);const body=await r.json() as any;assert.ok(!("cost" in body.items[0].product));}
});
test("API aplica permisos de módulo, rol y modo mayorista",async()=>{
 for(const [token,expected] of [[admin,200],[tienda,403],[inventario,403]] as const){const r=await fetch(`${server.baseUrl}/api/costs`,{headers:jsonHeaders(token)});assert.equal(r.status,expected);}
 const {invalidateRoleCache}=await import("../../../shared/middlewares/auth");const role=await ctx.prisma.roleModel.findUniqueOrThrow({where:{id:ctx.roleIds.tienda}});
 try{await ctx.prisma.roleModel.update({where:{id:role.id},data:{permissions:role.permissions.filter(p=>p!=="ventas-mayor")}});invalidateRoleCache(role.id);
 const p=await createProduct(ctx,{stockTienda:2});assert.equal((await postJson(server.baseUrl,"/api/sales",{items:[{productId:p.id,quantity:1,priceMode:"POR_MAYOR"}],payments:[{method:"QR",amount:80}]},tienda)).status,403);
 }finally{await ctx.prisma.roleModel.update({where:{id:role.id},data:{permissions:role.permissions}});invalidateRoleCache(role.id);}
});
test("23:59 de fin de mes y 00:00 siguiente pertenecen a días de negocio distintos",async()=>{
 const p=await createProduct(ctx);const saved=[];
 for(const saleDate of [new Date("2026-10-01T03:59:59.999Z"),new Date("2026-10-01T04:00:00.000Z")])saved.push(await ctx.prisma.sale.create({data:{userId:ctx.users.admin.userId,locationId:ctx.locationIds.tienda,type:"NORMAL",saleDate,total:100,items:{create:{productId:p.id,quantity:1,unitPrice:100,subtotal:100}}}}));
 for(const [date,id] of [["2026-09-30",saved[0].id],["2026-10-01",saved[1].id]] as const){const response=await fetch(`${server.baseUrl}/api/reports/sales?startDate=${date}&endDate=${date}&locationId=${ctx.locationIds.tienda}`,{headers:jsonHeaders(admin)});const body=await response.json() as any;assert.deepEqual(body.sales.map((s:any)=>s.id),[id]);}
});
test("snapshot de reporte impide duplicar páginas cuando aparece otra venta",async()=>{
 const p=await createProduct(ctx);const data={userId:ctx.users.admin.userId,locationId:ctx.locationIds.tienda,type:"NORMAL" as const,saleDate:new Date("2024-01-01T12:00:00Z"),total:100,items:{create:{productId:p.id,quantity:1,unitPrice:100,subtotal:100}}};
 const first=await ctx.prisma.sale.create({data});const second=await ctx.prisma.sale.create({data});
 const base=`${server.baseUrl}/api/reports/sales?startDate=2024-01-01&endDate=2024-01-01&locationId=${ctx.locationIds.tienda}&limit=1`;
 const page1=await(await fetch(base,{headers:jsonHeaders(admin)})).json() as any;await ctx.prisma.sale.create({data});
 const page2=await(await fetch(`${base}&page=2&snapshotMaxId=${page1.snapshotMaxId}`,{headers:jsonHeaders(admin)})).json() as any;
 assert.deepEqual([page1.sales[0].id,page2.sales[0].id],[second.id,first.id]);assert.equal(page2.pagination.total,2);
});
test("reconciliación local aborta con nulos sin inventar usuarios ni tipos de auditoría",async()=>{
 const sql=readFileSync(path.resolve(__dirname,"../../../../prisma/migrations/20260929_reconcile_production_schema/migration.sql"),"utf8");
 const checks=sql.match(/DO \$\$[\s\S]*?\$\$;/g)!;
 for(const [column,check] of [["userId",checks[0]],["targetType",checks[1]]] as const){
  await assert.rejects(ctx.prisma.$transaction(async tx=>{
   await tx.$executeRawUnsafe(`ALTER TABLE "AuditLog" ALTER COLUMN "${column}" DROP NOT NULL`);
   await tx.$executeRawUnsafe(`INSERT INTO "AuditLog" ("userId",action,"targetType") VALUES (${column==="userId"?"NULL":ctx.users.admin.userId},'TEST_NULL',${column==="targetType"?"NULL":"'TEST'"})`);
   await tx.$executeRawUnsafe(check);
  }),/NULL/);
 }
 const columns=await ctx.prisma.$queryRawUnsafe<Array<{is_nullable:string}>>(`SELECT is_nullable FROM information_schema.columns WHERE table_name='AuditLog' AND column_name IN ('userId','targetType')`);
 assert.ok(columns.every(c=>c.is_nullable==="NO"),"los DDL de prueba se revierten con la transacción");
});
test("reporte de marca suma solo sus líneas y mensual respeta la ubicación elegida",async()=>{
 const a=await createProduct(ctx),b=await createProduct(ctx);
 await ctx.prisma.product.update({where:{id:a.id},data:{brand:"MARCA-SEGUNDA"}});
 await ctx.prisma.sale.create({data:{userId:ctx.users.admin.userId,locationId:ctx.locationIds.tienda,type:"NORMAL",saleDate:new Date("2024-02-10T12:00:00Z"),total:180,items:{create:[{productId:a.id,quantity:1,unitPrice:100,subtotal:100},{productId:b.id,quantity:1,unitPrice:80,subtotal:80}]}}});
 const report=await(await fetch(`${server.baseUrl}/api/reports/sales?brand=MARCA-SEGUNDA&startDate=2024-02-01&endDate=2024-02-29`,{headers:jsonHeaders(admin)})).json() as any;
 assert.equal(report.summary.totalSales,100);assert.equal(report.sales[0].total,100);assert.equal(report.totalScope,"MATCHING_ITEMS");
 const monthly=await(await fetch(`${server.baseUrl}/api/reports/monthly?month=2024-02&locationId=${ctx.locationIds.tienda}`,{headers:jsonHeaders(admin)})).json() as any;
 assert.deepEqual(monthly.locations.map((l:any)=>l.location.id),[ctx.locationIds.tienda]);assert.equal(monthly.summary.totalSales,180);
});
test("importación mayorista no inventa POR MENOR y acepta columnas de la exportación",async()=>{
 const code=`SEGUNDA-NUEVO-${Date.now()}`;
 const send=async(row:Record<string,unknown>)=>{const form=new FormData();form.append("file",new Blob([invoiceBytes([row])],{type:"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}),"productos.xlsx");return fetch(`${server.baseUrl}/api/wholesale/import`,{method:"POST",headers:{authorization:`Bearer ${admin}`},body:form});};
 const row={"Código Fábrica":code,Producto:"Producto segunda importación",Marca:"TEST",Modelo:"TEST","Por mayor":80};
 const missing=await(await send(row)).json() as any;assert.equal(missing.errors,1);assert.equal(await ctx.prisma.product.count({where:{itemCode:code}}),0);
 try{const accepted=await(await send({...row,"Por menor":100})).json() as any;assert.equal(accepted.imported,1);const p=await ctx.prisma.product.findUniqueOrThrow({where:{itemCode:code}});assert.equal(Number(p.price1),100);assert.equal(Number(p.wholesalePrice),80);const edited=await fetch(`${server.baseUrl}/api/products/${p.id}`,{method:"PUT",headers:jsonHeaders(admin),body:JSON.stringify({price2:0,name:"Producto segunda importación editable"})});assert.equal(edited.status,200);}finally{await ctx.prisma.product.deleteMany({where:{itemCode:code}});}
});
test("usuario solo mayorista consulta su historial y nota sin abrir el módulo normal",async()=>{
 const p=await createProduct(ctx,{stockTienda:3});const sale=await(await postJson(server.baseUrl,"/api/wholesale",{items:[{productId:p.id,quantity:1,priceMode:"POR_MAYOR"}],payments:[{method:"QR",amount:80}]},tienda)).json() as any;
 const {invalidateRoleCache}=await import("../../../shared/middlewares/auth");const role=await ctx.prisma.roleModel.findUniqueOrThrow({where:{id:ctx.roleIds.tienda}});
 try{await ctx.prisma.roleModel.update({where:{id:role.id},data:{permissions:role.permissions.filter(p=>p!=="ventas")}});invalidateRoleCache(role.id);
 for(const url of [`/api/sales?type=MAYOR`,`/api/sales/${sale.id}/nota`])assert.equal((await fetch(server.baseUrl+url,{headers:jsonHeaders(tienda)})).status,200);
 assert.equal((await fetch(`${server.baseUrl}/api/sales`,{headers:jsonHeaders(tienda)})).status,403);
 }finally{await ctx.prisma.roleModel.update({where:{id:role.id},data:{permissions:role.permissions}});invalidateRoleCache(role.id);}
});
