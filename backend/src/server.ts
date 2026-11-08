import app from "./app";
import { config } from "./config";
import { startReplenishJob } from "./jobs/replenishJob";
import prisma from "./config/database";

const PORT = config.port;

const server = app.listen(PORT, () => {
  console.log(`Servidor corriendo en http://localhost:${PORT}`);
  startReplenishJob();
});

let shuttingDown = false;
function shutdown() {
  if (shuttingDown) return;
  shuttingDown = true;
  const deadline = setTimeout(() => process.exit(1), 25000);
  deadline.unref();
  server.close(async () => {
    await prisma.$disconnect();
    clearTimeout(deadline);
    process.exit(0);
  });
}
process.once("SIGTERM", shutdown);
process.once("SIGINT", shutdown);
