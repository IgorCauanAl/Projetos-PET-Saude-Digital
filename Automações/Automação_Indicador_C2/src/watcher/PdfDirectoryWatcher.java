package watcher;

import extract.PdfBoxExtractor;
import loader.ExcelLoader;
import model.Patient;
import transform.PatientTransformer;

import java.io.File;
import java.io.IOException;
import java.nio.file.*;
import java.util.List;

public class PdfDirectoryWatcher {

    public void startWatching(Path targetDir, File outputDir, String templatePath){

        try(WatchService watchService = FileSystems.getDefault().newWatchService()){

            WatchKey watchKey = targetDir.register(watchService, StandardWatchEventKinds.ENTRY_CREATE);
            System.out.println("Monitorando pasta: " + targetDir.toAbsolutePath());


            while(true){

                try{
                    WatchKey key = watchService.take();

                    for(WatchEvent<?> event : key.pollEvents()){

                        Path fileName = (Path) event.context();
                        Path fullPath = targetDir.resolve(fileName);

                        if(fileName.toString().toLowerCase().endsWith(".pdf")){
                            waitForFileCompletion(fullPath);

                            PdfBoxExtractor extractor = new PdfBoxExtractor();
                            String rawText = extractor.extractRawText(fullPath.toFile());

                            PatientTransformer transformer = new PatientTransformer();
                            List<Patient> patients = transformer.transform(rawText);

                            ExcelLoader loader = new ExcelLoader();
                            loader.generateReports(patients,outputDir,templatePath);

                            System.out.print("Arquivo processado: " + fileName);

                        }


                    }

                    boolean valid = key.reset();
                    if(!valid){
                        break;
                    }

                }catch(InterruptedException e){
                    Thread.currentThread().interrupt();
                    break;
                }catch( Exception e){
                    System.err.println("Erro ao processo arquivo" + e.getMessage());
                }

            }


        }catch(IOException e){
            System.err.println("Erro ao inicializar o WatchService: " + e.getMessage());
        }



    }

    //Garante a integridade fisica do arquivo no disco antes de tentar a leitura
    private void waitForFileCompletion(Path filePath){


        long previousSize = -1;
        int attempts = 0;

        while (attempts < 10){

            try{
                long currentSize = Files.size(filePath);

                if(currentSize > 0 && currentSize == previousSize){
                    System.out.println("Arquivo terminou de ser copiado com sucesso!");

                    return;

                }

                previousSize = currentSize;

                attempts++;

                Thread.sleep(1000);

            } catch (IOException e){



            } catch (InterruptedException e ){
                Thread.currentThread().interrupt();
                break;
            }

        }


    }

}
