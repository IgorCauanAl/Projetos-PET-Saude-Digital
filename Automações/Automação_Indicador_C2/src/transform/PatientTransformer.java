package transform;

import model.Indicators;
import model.Patient;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class PatientTransformer {

    private final List<IndicatorStrategy> strategies;

    private static final Pattern REGEX_CPF = Pattern.compile("\\b\\d{3}\\.?\\d{3}\\.?\\d{3}-?\\d{2}\\b");
    private static final Pattern PATIENT_BLOCK_PATTERN = Pattern.compile("(?=\\b\\d{6}\\s+[A-Z])");
    private static final Pattern REGEX_NAME_ENROLLMENT = Pattern.compile("^(\\d{6})\\s+([A-ZÀ-Ú\\s]+?)\\s+\\d{2}/\\d{2}/\\d{4}");
    private static final Pattern REGEX_PROFESSIONAL = Pattern.compile(
            "(?m)^\\s*(?:\\d{2}/\\d{2}/\\d{4}\\s+)?([A-ZÀ-Ú][A-ZÀ-Ú ]{3,}?)"
                    + "\\s*(?:\\d{11}\\s+)?\\d{1,3}(?:\\d{2}|FA|--)\\s*$"
    );

    public PatientTransformer() {
        this.strategies = List.of(
                new IndicatorAStrategy(),
                new IndicatorBStrategy(),
                new IndicatorCStrategy(),
                new IndicatorD1Strategy(),
                new IndicatorD2Strategy(),
                new IndicatorEStrategy()
        );
    }

    public List<Patient> transform(String rawText){
        List<Patient> patients = new ArrayList<>();

        if(rawText == null || rawText.isBlank()){
            System.err.print("Aviso:Texto bruto de entrada está nulo ou vazio! ");
            return patients;
        }


        String [] blocks = PATIENT_BLOCK_PATTERN.split(rawText);

        for(String block: blocks){
            if(isValidPatientBlock(block)){
                Patient patient = new Patient();
                Indicators indicators = new Indicators();
                patient.setIndicators(indicators);

                extractAndSetCpf(block,patient);
                extractNameAndMatricula(block,patient);
                extractAndSetProfessional(block,patient);

                for(IndicatorStrategy strategy: strategies){
                    strategy.process(block, indicators);
                }

                patients.add(patient);


            }


        }

        return patients;


    }

    private boolean isValidPatientBlock(String block){
        if(block == null || block.isBlank()){
            System.err.println("Aviso: Bloco de texto está nulo ou vazio!");
            return false;
        }

        if(block.trim().length() < 40){
            return false;
        }

        return true;
    }


    private void extractAndSetCpf(String block, Patient patient){

        Matcher matcher = REGEX_CPF.matcher(block);

        if(matcher.find()){

            String cpf = matcher.group();
            String cleanCPF = cpf.replaceAll("[^0-9]", "");

            patient.setCpf(cleanCPF);

        }

    }


   private void extractNameAndMatricula(String block, Patient patient){

     Matcher matcher =  REGEX_NAME_ENROLLMENT.matcher(block);

     if(matcher.find()){

         String enrollment = matcher.group(1);
         String name = matcher.group(2);

         patient.setEnrollment(enrollment);
         patient.setName(name);

     }

   }

   private void extractAndSetProfessional(String block, Patient patient){
        Matcher matcher = REGEX_PROFESSIONAL.matcher(block);

        if(matcher.find()){
            String professional = matcher.group(1).replaceAll("\\s+", " ").trim();
            patient.setLinkedProfessional(professional);

            return;

        }

            patient.setLinkedProfessional("PROFISSIONAL_NÃO_ENCONTRADO");

   }

}
