package transform;

import model.Indicators;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class IndicatorBStrategy implements IndicatorStrategy {

    private static final Pattern REGEX_B = Pattern.compile("B:\\s*Registrar mais (\\d+) consulta\\(s\\) até\\s*(\\d{2}/\\d{2}/\\d{4})");

    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("dd/MM/yyyy");

    @Override
    public void process(String patientBlock, Indicators indicator) {

        Matcher matcher = REGEX_B.matcher(patientBlock);

        if(matcher.find()){

            String textInquiries = matcher.group(1);
            String dateInquiries = matcher.group(2);

            try{
                Integer integerConversion = Integer.parseInt(textInquiries);
                indicator.setInquiriesB(integerConversion);

                LocalDate dateParsed = LocalDate.parse(dateInquiries, DATE_FORMATTER);
                indicator.setDateIndicatorsB(dateParsed);

            } catch(DateTimeParseException | NumberFormatException e){
                System.err.println("Aviso: Falha ao converter dados do Indicador B. Motivo: " + e.getMessage());
            }

        }
    }
}
