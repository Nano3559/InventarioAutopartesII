import { it, expect, vi } from "vitest";
import { saveSalePdf } from "./salePdf";
const mocks=vi.hoisted(()=>({addPage:vi.fn(),addImage:vi.fn(),save:vi.fn(),capture:vi.fn()}));
vi.mock("jspdf",()=>({jsPDF:vi.fn(()=>({internal:{pageSize:{getWidth:()=>210}},addPage:mocks.addPage,addImage:mocks.addImage,save:mocks.save}))}));
vi.mock("html2canvas",()=>({default:mocks.capture}));
it("un comprobante largo conserva su final en páginas adicionales",async()=>{
 mocks.capture.mockResolvedValue({width:500,height:2000,toDataURL:()=>"data:image/png;base64,test"});
 const receipt=document.createElement("div");receipt.id="receipt";
 await saveSalePdf(receipt,"venta.pdf");
 expect(mocks.addImage).toHaveBeenCalledTimes(3);expect(mocks.addPage).toHaveBeenCalledTimes(2);
 expect(mocks.addImage.mock.calls[2][3]).toBe(-594);expect(mocks.save).toHaveBeenCalledWith("venta.pdf");
 const clone=document.implementation.createHTMLDocument();clone.body.innerHTML='<div id="receipt" style="max-height:90vh;overflow:auto"><button>Descargar</button><p>Último producto</p></div>';
 mocks.capture.mock.calls[0][1].onclone(clone);
 expect(clone.getElementById("receipt")!.style.overflow).toBe("visible");expect(clone.querySelector("button")!.style.display).toBe("none");
});
