import html2canvas from "html2canvas";
import { jsPDF } from "jspdf";

/** Captura todo el comprobante y lo reparte entre páginas A4. */
export async function saveSalePdf(element: HTMLElement, filename: string) {
  const canvas = await html2canvas(element, {
    scale: 2, backgroundColor: "#151a22", height: element.scrollHeight,
    onclone: (copy) => {
      const receipt = copy.getElementById(element.id);
      if (!receipt) return;
      receipt.style.maxHeight = "none";
      receipt.style.overflow = "visible";
      receipt.querySelectorAll("button").forEach(button => { button.style.display = "none"; });
    },
  });
  const pdf = new jsPDF("p", "mm", "a4");
  const width = pdf.internal.pageSize.getWidth();
  const height = canvas.height * width / canvas.width;
  const image = canvas.toDataURL("image/png");
  for (let offset = 0; offset < height; offset += 297) {
    if (offset > 0) pdf.addPage();
    pdf.addImage(image, "PNG", 0, -offset, width, height);
  }
  pdf.save(filename);
}
