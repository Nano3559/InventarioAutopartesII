import app from "./app";
import { config } from "./config";
import { startReplenishJob } from "./jobs/replenishJob";

const PORT = config.port;

app.listen(PORT, () => {
  console.log(`Servidor corriendo en http://localhost:${PORT}`);
  startReplenishJob();
});
