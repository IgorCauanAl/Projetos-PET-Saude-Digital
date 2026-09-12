package loader;

import model.Indicators;
import model.Patient;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

public class ExcelLoader {

    private static final String BASE_OUTPUT_DIR = "Planilhas dos ACS";
    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("dd/MM/yyyy");

    public void generateReports(List<Patient> patients, String templatePath) {

        File template = new File(templatePath);

        if (patients == null || patients.isEmpty()) {
            return;
        }


        if(!template.exists() || !template.isFile()) {
            System.err.print("Aviso: Arquivo não existe ou é inválido!");
            return;
        }

        Map<String, List<Patient>> groupedPatients = groupPatientsByProfessional(patients);

        for(Map.Entry<String,List<Patient>> entry : groupedPatients.entrySet()){
            String rawName = entry.getKey();
            List<Patient> professionalPatients = entry.getValue();

            String sanitizedName = sanitizeDirectoryName(rawName);

            File outputDir =  createProfessionalDirectory(sanitizedName);

            populateAndSaveTemplate(outputDir,sanitizedName,professionalPatients, templatePath);


        }



    }


    //Método para agrupar pacientes por ACS
    private Map<String, List<Patient>> groupPatientsByProfessional(List<Patient> patients) {

        if(patients == null || patients.isEmpty()){
            System.err.print("Aviso: Campo dos profissionais ou pacientes está nulo ou inválido");
            return Map.of();
        }

        return patients.stream()
                .collect(Collectors.groupingBy(p -> p.getLinkedProfessional() != null ? p.getLinkedProfessional() : "Profissional para o paciente não está informado"));

    }




    //Método para limpar o nome do profisisonal para o sistema de arquivos
    private String sanitizeDirectoryName(String rawName) {

        if(rawName == null || rawName.isBlank()){
            System.err.print("Aviso: O nome do Agente Comunitário de Saúde está em branco ou é inválido");
            return "PROFISSIONAL_NAO_INFORMADO";
        }

       String sanitedName = rawName.replaceAll("[^a-zA-Z0-9_ ]", "").trim();


        return sanitedName;

    }

    //Método para criar a pasta física com o nome do ACS no SO
    private File createProfessionalDirectory(String sanitizedName) {

        File dir = new File(BASE_OUTPUT_DIR, sanitizedName);

        boolean sucess = true;

        if(!dir.exists()){
            System.err.print("Aviso: Diretório não existe!, criando uma...");
            sucess = dir.mkdirs();

        }

        if(sucess){
            System.out.println("Criando a pasta pai e seus filhos...");
        }else{
            System.err.print("Aviso: Sistema Operacional não permitiu a criação das pastas");
        }

        return dir;

    }

    //Abre a planilha modelo, clona o conteúdo e preenche os pacientes e gravar o arquivo final
    private void populateAndSaveTemplate(File outputDir, String professionalName, List<Patient> patientList, String templatePath) {


        try (FileInputStream fis = new FileInputStream(templatePath);
             Workbook workbook = new XSSFWorkbook(fis)) {

                 Sheet sheet = workbook.getSheetAt(0);

                 int startRow = 6;

                 for(int i = 0 ; i < patientList.size(); i++){

                     Patient patient = patientList.get(i);
                     int currentRowNum = startRow + i;

                     Row row = sheet.getRow(currentRowNum);
                     if (row == null) {
                         row = sheet.createRow(currentRowNum);
                     }

                     fillPatientRow(row,patient);

                 }

                File outputFile = new File(outputDir, "Relatório C2 " + professionalName + ".xlsx");


            try(FileOutputStream fos = new FileOutputStream(outputFile)){
                workbook.write(fos);
            }

             }
        catch(IOException e){
            System.err.print("Aviso: Erro na leitura/escrito no Excel ");
        }
    }


    //Escreve os atributos do paciente e do seus indicadores em sua respectiva célula na planilha
    private void fillPatientRow(Row row, Patient patient) {

        Cell cellName = row.createCell(0);
        cellName.setCellValue(patient.getName() != null ? patient.getName() : "");

        Cell cellCPF = row.createCell(1);
        cellCPF.setCellValue(patient.getCpf() != null ? patient.getCpf() : "");


        Cell cellBirthDate = row.createCell(2);
        String formattedDate = (patient.getDateOfBirth() != null) ? DATE_FORMATTER.format(patient.getDateOfBirth()) : "";
        cellBirthDate.setCellValue(formattedDate);

        Cell cellMa = row.createCell(5);
        cellMa.setCellValue(patient.getMa() != null ? patient.getMa() : "");

        Indicators ind = patient.getIndicators();

        if(ind != null){

            //Indicador A
            Cell cellDataA = row.createCell(10);
            String formattedDateIndicatorsA = (ind.getDateIndicatorsA() != null) ? DATE_FORMATTER.format(ind.getDateIndicatorsA()) : "";
            cellDataA.setCellValue(formattedDateIndicatorsA);

            //Indicador B
            Cell cellDataB = row.createCell(13);
            String formattedDateIndicatorsB = (ind.getDateIndicatorsB() != null) ? DATE_FORMATTER.format(ind.getDateIndicatorsB()) : "";
            cellDataB.setCellValue(formattedDateIndicatorsB);

            //consultas pendentes do indicador B
            Cell cellInquiriesB = row.createCell(14);
            if (ind.getInquiriesB() != null) {
                cellInquiriesB.setCellValue(ind.getInquiriesB());
            } else {
                cellInquiriesB.setBlank();
            }

            //Indicador C
            Cell cellDataC = row.createCell(16);
            String formattedDateIndicatorsC = (ind.getDateIndicatorsC() != null) ? DATE_FORMATTER.format(ind.getDateIndicatorsC()) : "";
            cellDataC.setCellValue(formattedDateIndicatorsC);

            //aferições do indicador C
            Cell cellMeasurementC = row.createCell(17);
            if (ind.getMeasurementC() != null) {
                cellMeasurementC.setCellValue(ind.getMeasurementC());
            } else {
                cellMeasurementC.setBlank();
            }

            //Data do indicador D1
            Cell cellDataD1 = row.createCell(19);
            String formattedDateIndicatorsD1 = (ind.getDateIndicatorsD1() != null) ? DATE_FORMATTER.format(ind.getDateIndicatorsD1()) : "";
            cellDataD1.setCellValue(formattedDateIndicatorsD1);


            //Data do indicador D2
            Cell cellDataD2 = row.createCell(21);
            String formattedDateIndicatorsD2 = (ind.getDateIndicatorsD2() != null) ? DATE_FORMATTER.format(ind.getDateIndicatorsD2()) : "";
            cellDataD2.setCellValue(formattedDateIndicatorsD2);

            //Visita D1
            Cell cellVisitsD1 = row.createCell(20);
            if (ind.getPendingVisitsD1() != null) {
                cellVisitsD1.setCellValue(ind.getPendingVisitsD1());
            } else {
                cellVisitsD1.setBlank();
            }

            //Visita D2
            Cell cellVisitsD2 = row.createCell(22);
            if (ind.getPendingVisitsD2() != null) {
                cellVisitsD2.setCellValue(ind.getPendingVisitsD2());
            } else {
                cellVisitsD2.setBlank();
            }

            //Data do indicador E
            Cell cellDataE = row.createCell(24);
            String formattedDateIndicatorsE= (ind.getDateIndicatorsE() != null) ? DATE_FORMATTER.format(ind.getDateIndicatorsE()) : "";
            cellDataE.setCellValue(formattedDateIndicatorsE);



        }
    }


}