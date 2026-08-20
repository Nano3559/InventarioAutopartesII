import { MessageCircle } from "lucide-react";

export default function WhatsAppButton() {
  return (
    <button
      onClick={() => alert("Próximamente podrás contactarnos por WhatsApp. ¡Por ahora escríbenos a contacto@repuestopro.com!")}
      className="fixed bottom-6 right-6 z-50 w-14 h-14 bg-green-500 hover:bg-green-600 rounded-full flex items-center justify-center shadow-lg shadow-green-500/30 transition-all hover:scale-110 cursor-pointer"
      title="Contactar por WhatsApp (próximamente)"
    >
      <MessageCircle size={26} className="text-white" />
    </button>
  );
}
