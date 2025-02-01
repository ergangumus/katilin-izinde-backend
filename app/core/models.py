"""
Database models.
"""
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.utils import timezone


class UserManager(BaseUserManager):
    """Manager for users."""

    def create_user(self, email, password=None, **extra_fields):
        """Create, save and return a new user."""
        if not email:
            raise ValueError('User must have an email address.')
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password):
        """Create and return a new superuser."""
        user = self.create_user(email, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)

        return user


class User(AbstractBaseUser, PermissionsMixin):
    """User in the system."""
    email = models.EmailField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'


# --------------------------------------------------------------------
# 1. Ortak Alanlar: BaseModel
# --------------------------------------------------------------------
class BaseModel(models.Model):
    """
    Proje genelinde tekrar eden alanları soyutlamak (DRY) adına oluşturulmuş,
    abstract bir model. Tüm modeller bu sınıftan miras alarak
    is_active, created_at, updated_at vb. ortak alanları kullanabilir.
    """
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']  # Örnek: en yeni kayıtlar önce gelsin.


# --------------------------------------------------------------------
# 2. Kurban Modeli
# --------------------------------------------------------------------
class Victim(BaseModel):
    """
    Olayın/Case'in kurbanını temsil eder.
    Bir Case'e genellikle tek bir kurban atanacağını varsayıyorsanız
    Case ile OneToOneField veya ForeignKey seçeneklerini değerlendirebilirsiniz.
    Burada bağımsız bir modeldir; Case modeli de Victim ile ilişkili olabilir.
    """
    name = models.CharField(max_length=200)
    age = models.PositiveIntegerField()
    description = models.TextField(blank=True, null=True)
    time_of_death = models.DateTimeField(blank=True, null=True)
    cause_of_death = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.name


# --------------------------------------------------------------------
# 3. Vaka (Case) Modeli
# --------------------------------------------------------------------
class Case(BaseModel):
    """
    Bir cinayet vakasını (olayı) temsil eder.
    Burada 'victim' alanı, bir Case'in tek bir kurbanı olduğu senaryoya uygundur.
    Eğer bir vakada birden çok kurban olabiliyorsa, M2M veya başka ilişki kullanabilirsiniz.
    """
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)

    # Eğer her vaka tek bir kurbana sahipse:
    # on_delete=SET_NULL ile kurban silinince vakanın yok olmamasını da tercih edebilirsiniz.
    victim = models.OneToOneField(
        Victim,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='case'  # Kurbandan case'e ulaşmak için victim.case
    )

    def __str__(self):
        return self.title


# --------------------------------------------------------------------
# 4. Mekan (Location) Modeli
# --------------------------------------------------------------------
class Location(BaseModel):
    """
    Vakanın geçtiği mekanlar (ör. cinayet mahal(i), malikâne odası, mahzen vb.)
    is_crime_scene=True => olay yeri (primary crime scene) olduğunu ifade edebilir.
    """
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name='locations'
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    is_crime_scene = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} (Case: {self.case.title})"


# --------------------------------------------------------------------
# 5. Şüpheli (Suspect) Modeli
# --------------------------------------------------------------------
class Suspect(BaseModel):
    """
    Bir vakada şüpheli konumundaki kişileri temsil eder.
    relation_to_victim => Kurbanla akraba, iş arkadaşı vb. ilişki tanımı için.
    Alibi, clothing_description gibi alanlar sorgu süreçlerinde önemli olabilir.
    """
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name='suspects'
    )
    name = models.CharField(max_length=200)
    age = models.PositiveIntegerField()
    relation_to_victim = models.CharField(
        max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    alibi = models.TextField(blank=True, null=True)
    clothing_description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} (Case: {self.case.title})"


# --------------------------------------------------------------------
# 6. Motive Modeli
# --------------------------------------------------------------------
class Motive(BaseModel):
    """
    Şüphelinin olayla ilgili potansiyel güdülerini tutar.
    Bir şüphelinin birden fazla motivasyonu olabilir (miras, kıskançlık, intikam vb.).
    """
    suspect = models.ForeignKey(
        Suspect,
        on_delete=models.CASCADE,
        related_name='motives'
    )
    motive_description = models.TextField(blank=True, null=True)

    def __str__(self):
        # İlk 50 karakteri göstererek kısaltma yapabilirsiniz.
        return f"Motive for {self.suspect.name}: {self.motive_description[:50]}"


# --------------------------------------------------------------------
# 7. İfade (Testimony) Modeli
# --------------------------------------------------------------------
class Testimony(BaseModel):
    """
    Şüphelinin (veya tanığın) emniyette/polis önünde verdiği ifadenin kaydı.
    given_at => ifadenin hangi tarihte alındığı.
    testimony => ifadenin tam metni.
    """
    suspect = models.ForeignKey(
        Suspect,
        on_delete=models.CASCADE,
        related_name='testimonies'
    )
    given_at = models.DateTimeField(default=timezone.now)
    testimony = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Testimony of {self.suspect.name} at {self.given_at}"


# --------------------------------------------------------------------
# 8. İpucu (Clue) Modeli
# --------------------------------------------------------------------
class Clue(BaseModel):
    """
    Olayla ilgili bulunan ipuçlarını temsil eder.
    Örneğin: Parmak izleri, kan lekesi, kırık bir vazo vb.
    found_at => ipucunun ne zaman bulunduğu.
    related_suspect => ipucunun doğrudan bir şüpheliyle ilişkili olduğu senaryo (isteğe bağlı).
    """
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name='clues'
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='clues'
    )
    description = models.TextField(blank=True, null=True)
    found_at = models.DateTimeField(default=timezone.now)
    related_suspect = models.ForeignKey(
        Suspect,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='clues'
    )

    def __str__(self):
        return f"[{self.case.title}] Clue at {self.location.name}"


# --------------------------------------------------------------------
# 9. Delil (Evidence) Modeli
# --------------------------------------------------------------------
class Evidence(BaseModel):
    """
    Fiziksel veya dijital delil kayıtları (otopsi raporu, belge, kırık kadeh vb.).
    - obtained_from: Bu delil hangi mekândan ele geçirildi?
    - related_suspect: Bu delil hangi şüpheliyi işaret ediyor olabilir?
    """
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name='evidences'
    )
    description = models.TextField()
    obtained_from = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='evidences'
    )
    date_obtained = models.DateTimeField(default=timezone.now)
    related_suspect = models.ForeignKey(
        Suspect,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='related_evidences'
    )

    def __str__(self):
        return f"Evidence (Case: {self.case.title})"


# --------------------------------------------------------------------
# 10. Mesaj (Message) Modeli
# --------------------------------------------------------------------
class Message(BaseModel):
    """
    Kurban, şüpheliler veya farklı taraflar arasındaki mesajlaşmalar.
    content: Mesaj içeriği (WhatsApp, SMS, Email vb.).
    related_suspect: Bu mesaj hangi şüpheliyle ilişkili?
    """
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.CharField(max_length=200, blank=True, null=True)
    receiver = models.CharField(max_length=200, blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)
    content = models.TextField()
    related_suspect = models.ForeignKey(
        Suspect,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='messages'
    )

    def __str__(self):
        return f"Message from {self.sender} to {self.receiver} (Case: {self.case.title})"


# --------------------------------------------------------------------
# 11. Arama Kaydı (CallRecord) Modeli
# --------------------------------------------------------------------
class CallRecord(BaseModel):
    """
    Telefon görüşmesi kayıtları.
    duration => saniye cinsinden arama süresi.
    related_suspect => Bu kayıt belirli bir şüpheli ile ilişkilendirilebilirse.
    """
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name='calls'
    )
    caller = models.CharField(max_length=200, blank=True, null=True)
    callee = models.CharField(max_length=200, blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)
    duration = models.PositiveIntegerField(
        help_text="Call duration in seconds",
        blank=True,
        null=True
    )
    related_suspect = models.ForeignKey(
        Suspect,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='call_records'
    )

    def __str__(self):
        return f"Call {self.caller} -> {self.callee} at {self.timestamp}"
