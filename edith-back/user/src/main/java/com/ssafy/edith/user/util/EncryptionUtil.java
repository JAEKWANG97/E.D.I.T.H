package com.ssafy.edith.user.util;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;
import java.security.MessageDigest;
import java.util.Base64;

@Component
public class EncryptionUtil {
    private static final String ALGORITHM = "AES";

    private static String secretKey;

    public EncryptionUtil(@Value("${encryption.secret-key}") String secretKey) {
        EncryptionUtil.secretKey = secretKey;
    }

    private static SecretKeySpec getSecretKeySpec() throws Exception { //SECRET_KEY SHA-256으로 동적생성
        MessageDigest sha = MessageDigest.getInstance("SHA-256");
        byte[] key = sha.digest(secretKey.getBytes("UTF-8"));
        return new SecretKeySpec(key, ALGORITHM);
    }

    public static String encrypt(String plainText) { //AES 알고리즘을 통해 GitLab Personal Access Token 암호화
        try {
            SecretKeySpec keySpec = getSecretKeySpec();
            Cipher cipher = Cipher.getInstance(ALGORITHM);
            cipher.init(Cipher.ENCRYPT_MODE, keySpec);
            byte[] encryptedBytes = cipher.doFinal(plainText.getBytes("UTF-8"));
            return Base64.getEncoder().encodeToString(encryptedBytes);
        } catch (Exception e) {
            throw new RuntimeException("GitLab Personal Access Token 암호화에 실패했습니다.", e);
        }
    }

    public static String decrypt(String encryptedText) {
        try {
            SecretKeySpec keySpec = getSecretKeySpec();
            Cipher cipher = Cipher.getInstance(ALGORITHM);
            cipher.init(Cipher.DECRYPT_MODE, keySpec);
            byte[] decodedBytes = Base64.getDecoder().decode(encryptedText);
            byte[] decryptedBytes = cipher.doFinal(decodedBytes);
            return new String(decryptedBytes, "UTF-8");
        } catch (Exception e) {
            throw new RuntimeException("GitLab Personal Access Token 복호화에 실패했습니다.", e);
        }
    }

}
