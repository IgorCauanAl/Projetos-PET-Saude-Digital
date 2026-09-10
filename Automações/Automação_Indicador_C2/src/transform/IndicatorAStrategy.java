package transform;

import model.Indicators;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class IndicatorAStrategy implements IndicatorStrategy{

    //Regex para capturar a data limite da consulta
    private static final Pattern REGEX_A = Pattern.compile("A:\\s*Não registrou 1 consulta até\\s*(\\d{2}/\\d{2}/\\d{4})");
    //Formatação para a data
    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("dd/MM/yyyy");

    @Override
    public void process(String patientBlock, Indicators indicators) {
        Matcher matcher = REGEX_A.matcher(patientBlock);


        if(matcher.find()){
            String textDate = matcher.group(1);

            try{
                LocalDate dateParsed = LocalDate.parse(textDate, DATE_FORMATTER);
                indicators.setDateIndicatorsA(dateParsed);
            } catch(DateTimeParseException e){
                System.err.println("Data inválida capturada no indicador A "+ e.getMessage());
            }


        }





    }
}
