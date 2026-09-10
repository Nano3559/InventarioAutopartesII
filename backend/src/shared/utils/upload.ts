import multer from "multer";

const EXCEL_MIMES = new Set([
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/vnd.ms-excel",
]);

/**
 * Upload compartido para importación de Excel (wholesale/products):
 * memoria + máx 10 MB + solo archivos .xlsx/.xls (extensión o MIME).
 * Rechaza cualquier otro tipo con code "INVALID_FILE_TYPE" (mapeado a 400
 * por el errorHandler central).
 */
export const excelUpload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 10 * 1024 * 1024, files: 1 },
  fileFilter: (_req, file, cb) => {
    const validExt = /\.(xlsx|xls)$/i.test(file.originalname);
    if (validExt || EXCEL_MIMES.has(file.mimetype)) {
      return cb(null, true);
    }
    const err: any = new Error("Tipo de archivo no permitido");
    err.code = "INVALID_FILE_TYPE";
    cb(err);
  },
});